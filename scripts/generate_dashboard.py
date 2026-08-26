#!/usr/bin/env python3
"""
JSearch Dashboard Generator
Reads all application folders and produces dashboard/index.html
Usage: python3 scripts/generate_dashboard.py
Run from the jsearch/ project root.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_project_root, load_yaml


def collect_applications(applications_dir):
    """Walk application folders and aggregate data."""
    apps = []
    if not os.path.exists(applications_dir):
        return apps

    for folder in sorted(os.listdir(applications_dir)):
        folder_path = os.path.join(applications_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        job_path = os.path.join(folder_path, "job.yaml")
        status_path = os.path.join(folder_path, "status.yaml")

        if not os.path.exists(job_path):
            continue

        job = load_yaml(job_path)
        status = load_yaml(status_path) if os.path.exists(status_path) else {}

        company = job.get("company", {})
        role = job.get("role", {})
        urls = job.get("urls", {})

        apps.append({
            "id": job.get("id", folder),
            "folder": folder,
            "company": company.get("name", "Unknown"),
            "domain": company.get("domain", ""),
            "employee_count": company.get("employee_count"),
            "founded": company.get("founded"),
            "title": role.get("title", "Unknown"),
            "location": role.get("location", ""),
            "remote": role.get("remote", False),
            "seniority": role.get("seniority", ""),
            "posted_on": role.get("posted_on", ""),
            "linkedin_url": urls.get("linkedin", ""),
            "source": job.get("source", ""),
            "ingested_at": job.get("ingested_at", ""),
            "status": status.get("current_status", "new"),
            "score": status.get("score"),
            "tier": status.get("tier", ""),
            "cv_generated": (status.get("materials") or {}).get("cv_generated", False),
            "cover_letter_generated": (status.get("materials") or {}).get("cover_letter_generated", False),
            "applied_on": (status.get("application") or {}).get("applied_on"),
            "next_action": status.get("next_action", ""),
            "timeline": status.get("timeline", []),
        })

    return apps


def compute_stats(apps):
    """Compute summary statistics."""
    total = len(apps)
    analyzed = sum(1 for a in apps if a["score"] is not None)
    applied = sum(1 for a in apps if a["status"] in ("applied", "follow_up", "response", "interview", "offer", "rejected"))
    responses = sum(1 for a in apps if a["status"] in ("response", "interview", "offer"))
    interviews = sum(1 for a in apps if a["status"] in ("interview", "offer"))
    offers = sum(1 for a in apps if a["status"] == "offer")
    ready = sum(1 for a in apps if a["status"] == "ready")

    return {
        "total": total,
        "analyzed": analyzed,
        "applied": applied,
        "ready": ready,
        "responses": responses,
        "interviews": interviews,
        "offers": offers,
        "response_rate": round(responses / applied * 100, 1) if applied > 0 else 0,
        "interview_rate": round(interviews / applied * 100, 1) if applied > 0 else 0,
        "avg_score": round(sum(a["score"] for a in apps if a["score"] is not None) / analyzed, 1) if analyzed > 0 else 0,
    }


def generate_html(apps, stats):
    """Generate self-contained dashboard HTML."""
    data_json = json.dumps({"apps": apps, "stats": stats}, default=str, ensure_ascii=False)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSearch Dashboard</title>
<style>
:root {{
  --purple: #a87eff;
  --purple-fill: #8c4aec;
  --purple-glow: rgba(168, 126, 255, 0.18);
  --purple-border: rgba(168, 126, 255, 0.35);
  --black: #0a0a0a;
  --dark: #141414;
  --card: #1c1c1c;
  --white: #fefefe;
  --gray: #2e2e2e;
  --gray-light: #a0a0a0;
  --text: #e8e8e8;
  --text-dim: #a0a0a0;
  --radius: 14px;
  --radius-sm: 9px;
  --green: #22c55e;
  --green-glow: rgba(34, 197, 94, 0.15);
  --amber: #f59e0b;
  --amber-glow: rgba(245, 158, 11, 0.15);
  --red: #ef4444;
  --red-glow: rgba(239, 68, 68, 0.12);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: var(--black);
  color: var(--text);
  font-family: -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  padding: 0;
}}
.header {{
  background: var(--black);
  text-align: center;
  padding: 40px 20px 30px;
  position: relative;
}}
.header::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 200px;
  background: radial-gradient(ellipse at center top, rgba(168,126,255,0.15) 0%, transparent 70%);
  pointer-events: none;
}}
.header::after {{
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--purple-border), transparent);
}}
.header h1 {{
  font-size: 28px;
  font-weight: 700;
  color: var(--white);
  position: relative;
}}
.header h1 em {{
  color: var(--purple);
  font-style: normal;
}}
.header .subtitle {{
  color: var(--text-dim);
  font-size: 13px;
  margin-top: 8px;
  position: relative;
}}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px 20px; }}

/* Stats Cards */
.stats-row {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}}
@media (max-width: 768px) {{ .stats-row {{ grid-template-columns: repeat(2, 1fr); }} }}
.stat-card {{
  background: var(--card);
  border: 1.5px solid var(--gray);
  border-radius: var(--radius);
  padding: 18px 20px;
  text-align: center;
}}
.stat-card:hover {{ border-color: var(--purple-border); }}
.stat-value {{
  font-size: 32px;
  font-weight: 700;
  color: var(--white);
  line-height: 1;
}}
.stat-label {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-top: 6px;
}}

/* Controls */
.controls {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  align-items: center;
}}
.controls input, .controls select {{
  background: var(--black);
  border: 1.5px solid var(--gray);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 14px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}}
.controls input:focus, .controls select:focus {{
  border-color: var(--purple);
  box-shadow: 0 0 0 3px var(--purple-glow);
}}
.controls input {{ flex: 1; min-width: 180px; }}
.view-toggle {{
  display: flex;
  gap: 0;
  margin-left: auto;
}}
.view-btn {{
  background: var(--card);
  border: 1.5px solid var(--gray);
  color: var(--text-dim);
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}}
.view-btn:first-child {{ border-radius: var(--radius-sm) 0 0 var(--radius-sm); }}
.view-btn:last-child {{ border-radius: 0 var(--radius-sm) var(--radius-sm) 0; border-left: none; }}
.view-btn.active {{
  background: var(--purple-fill);
  border-color: var(--purple);
  color: var(--white);
}}

/* Score Badges */
.score-badge {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 700;
}}
.score-excellent {{ background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.score-good {{ background: var(--purple-glow); color: var(--purple); border: 1px solid var(--purple-border); }}
.score-moderate {{ background: var(--amber-glow); color: var(--amber); border: 1px solid rgba(245,158,11,0.3); }}
.score-low {{ background: var(--red-glow); color: var(--red); border: 1px solid rgba(239,68,68,0.3); }}
.score-none {{ background: var(--gray); color: var(--text-dim); border: 1px solid var(--gray); }}

/* Status Pills */
.status-pill {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 3px 10px;
  border-radius: 99px;
  text-transform: uppercase;
}}
.status-new {{ background: var(--gray); color: var(--text-dim); }}
.status-analyzed {{ background: var(--purple-glow); color: var(--purple); border: 1px solid var(--purple-border); }}
.status-preparing {{ background: var(--amber-glow); color: var(--amber); border: 1px solid rgba(245,158,11,0.3); }}
.status-ready {{ background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.status-applied {{ background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }}
.status-follow_up {{ background: var(--amber-glow); color: var(--amber); border: 1px solid rgba(245,158,11,0.3); }}
.status-response {{ background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.status-interview {{ background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.status-offer {{ background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.status-rejected {{ background: var(--red-glow); color: var(--red); border: 1px solid rgba(239,68,68,0.3); }}
.status-withdrawn {{ background: var(--gray); color: var(--text-dim); }}

/* Table View */
.table-view {{ width: 100%; }}
table {{
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
  border-radius: var(--radius);
  overflow: hidden;
  border: 1.5px solid var(--gray);
}}
th {{
  background: var(--dark);
  color: var(--text-dim);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-align: left;
  padding: 12px 14px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}}
th:hover {{ color: var(--purple); }}
th .sort-arrow {{ font-size: 10px; margin-left: 4px; }}
td {{
  padding: 12px 14px;
  border-top: 1px solid var(--gray);
  font-size: 13px;
  vertical-align: middle;
}}
tr:hover td {{ background: rgba(168,126,255,0.04); }}
.company-cell {{
  font-weight: 600;
  color: var(--white);
}}
.company-cell a {{
  color: var(--white);
  text-decoration: none;
}}
.company-cell a:hover {{ color: var(--purple); }}
.company-domain {{
  font-size: 11px;
  color: var(--text-dim);
  font-weight: 400;
}}
.location-cell {{ color: var(--text-dim); font-size: 12px; }}
.date-cell {{ color: var(--text-dim); font-size: 12px; white-space: nowrap; }}
.remote-badge {{
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 99px;
  background: var(--green-glow);
  color: var(--green);
  border: 1px solid rgba(34,197,94,0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* Kanban View */
.kanban-view {{ display: none; }}
.kanban-view.active {{ display: flex; }}
.kanban-scroll {{
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 20px;
}}
.kanban-column {{
  min-width: 260px;
  max-width: 300px;
  flex-shrink: 0;
}}
.kanban-col-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 8px;
}}
.kanban-col-title {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-dim);
}}
.kanban-col-count {{
  font-size: 10px;
  font-weight: 700;
  background: var(--gray);
  color: var(--text-dim);
  padding: 1px 7px;
  border-radius: 99px;
}}
.kanban-card {{
  background: var(--card);
  border: 1.5px solid var(--gray);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 8px;
  transition: border-color 0.2s;
}}
.kanban-card:hover {{ border-color: var(--purple-border); }}
.kanban-card-company {{
  font-size: 14px;
  font-weight: 600;
  color: var(--white);
  margin-bottom: 2px;
}}
.kanban-card-role {{
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 8px;
}}
.kanban-card-meta {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.kanban-card-location {{
  font-size: 11px;
  color: var(--text-dim);
}}
.kanban-card a {{
  color: inherit;
  text-decoration: none;
}}

/* Detail Panel */
.detail-row {{ display: none; }}
.detail-row.open {{ display: table-row; }}
.detail-content {{
  background: var(--black);
  padding: 20px;
  border-top: 1px solid var(--purple-border);
}}
.detail-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}}
@media (max-width: 768px) {{ .detail-grid {{ grid-template-columns: 1fr; }} }}
.detail-section h4 {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 8px;
}}
.detail-section p {{
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
}}
.timeline-item {{
  font-size: 12px;
  color: var(--text-dim);
  padding: 4px 0;
  border-left: 2px solid var(--gray);
  padding-left: 12px;
  margin-left: 4px;
}}
.timeline-item .t-date {{ color: var(--purple); font-weight: 600; }}

/* Footer */
.footer {{
  text-align: center;
  padding: 30px 20px;
  color: var(--text-dim);
  font-size: 12px;
  border-top: 1px solid var(--gray);
  margin-top: 40px;
}}

/* Empty State */
.empty-state {{
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
}}
.empty-state h3 {{ color: var(--white); margin-bottom: 8px; }}
</style>
</head>
<body>
<div class="header">
  <h1>JSearch <em>Dashboard</em></h1>
  <p class="subtitle">Last updated: {generated_at}</p>
</div>

<div class="container">
  <div class="stats-row" id="statsRow"></div>

  <div class="controls">
    <input type="text" id="searchInput" placeholder="Search company or role...">
    <select id="statusFilter">
      <option value="all">All Statuses</option>
      <option value="new">New</option>
      <option value="analyzed">Analyzed</option>
      <option value="preparing">Preparing</option>
      <option value="ready">Ready</option>
      <option value="applied">Applied</option>
      <option value="follow_up">Follow-up</option>
      <option value="response">Response</option>
      <option value="interview">Interview</option>
      <option value="offer">Offer</option>
      <option value="rejected">Rejected</option>
      <option value="withdrawn">Withdrawn</option>
    </select>
    <select id="sortSelect">
      <option value="score_desc">Score (High to Low)</option>
      <option value="score_asc">Score (Low to High)</option>
      <option value="date_desc">Date (Newest)</option>
      <option value="date_asc">Date (Oldest)</option>
      <option value="company_asc">Company (A-Z)</option>
    </select>
    <div class="view-toggle">
      <button class="view-btn active" data-view="table">Table</button>
      <button class="view-btn" data-view="kanban">Kanban</button>
    </div>
  </div>

  <div class="table-view active" id="tableView">
    <table>
      <thead>
        <tr>
          <th data-sort="company">Company <span class="sort-arrow"></span></th>
          <th data-sort="title">Role <span class="sort-arrow"></span></th>
          <th data-sort="score">Score <span class="sort-arrow"></span></th>
          <th data-sort="status">Status <span class="sort-arrow"></span></th>
          <th data-sort="location">Location <span class="sort-arrow"></span></th>
          <th data-sort="seniority">Level <span class="sort-arrow"></span></th>
          <th data-sort="posted_on">Posted <span class="sort-arrow"></span></th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>

  <div class="kanban-view" id="kanbanView">
    <div class="kanban-scroll" id="kanbanScroll"></div>
  </div>
</div>

<div class="footer">
  JSearch AI Assistant Flow &middot; Powered by Claude Code
</div>

<script>
const APP_DATA = {data_json};

const STATUSES_ORDER = ['new','analyzed','preparing','ready','applied','follow_up','response','interview','offer','rejected','withdrawn'];
const STATUS_LABELS = {{
  new:'New', analyzed:'Analyzed', preparing:'Preparing', ready:'Ready',
  applied:'Applied', follow_up:'Follow-up', response:'Response',
  interview:'Interview', offer:'Offer', rejected:'Rejected', withdrawn:'Withdrawn'
}};

let currentView = localStorage.getItem('jsearch-view') || 'table';
let currentSort = 'score_desc';
let currentStatusFilter = 'all';
let currentSearch = '';

function scoreClass(s) {{
  if (s === null || s === undefined) return 'score-none';
  if (s >= 85) return 'score-excellent';
  if (s >= 70) return 'score-good';
  if (s >= 50) return 'score-moderate';
  return 'score-low';
}}

function formatDate(d) {{
  if (!d) return '';
  try {{ return new Date(d).toLocaleDateString('en-US', {{month:'short', day:'numeric'}}); }}
  catch {{ return ''; }}
}}

function renderStats() {{
  const s = APP_DATA.stats;
  document.getElementById('statsRow').innerHTML = `
    <div class="stat-card"><div class="stat-value">${{s.total}}</div><div class="stat-label">Total Jobs</div></div>
    <div class="stat-card"><div class="stat-value">${{s.applied}}</div><div class="stat-label">Applied</div></div>
    <div class="stat-card"><div class="stat-value">${{s.response_rate}}%</div><div class="stat-label">Response Rate</div></div>
    <div class="stat-card"><div class="stat-value">${{s.interview_rate}}%</div><div class="stat-label">Interview Rate</div></div>
  `;
}}

function getFilteredApps() {{
  let apps = [...APP_DATA.apps];
  if (currentStatusFilter !== 'all') apps = apps.filter(a => a.status === currentStatusFilter);
  if (currentSearch) {{
    const q = currentSearch.toLowerCase();
    apps = apps.filter(a => a.company.toLowerCase().includes(q) || a.title.toLowerCase().includes(q));
  }}
  // Sort
  apps.sort((a, b) => {{
    switch(currentSort) {{
      case 'score_desc': return (b.score||0) - (a.score||0);
      case 'score_asc': return (a.score||0) - (b.score||0);
      case 'date_desc': return new Date(b.posted_on||0) - new Date(a.posted_on||0);
      case 'date_asc': return new Date(a.posted_on||0) - new Date(b.posted_on||0);
      case 'company_asc': return a.company.localeCompare(b.company);
      default: return 0;
    }}
  }});
  return apps;
}}

function renderTable() {{
  const apps = getFilteredApps();
  const tbody = document.getElementById('tableBody');
  if (!apps.length) {{
    tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><h3>No jobs found</h3><p>Drop a Clay CSV into inbox/clay-exports/ and run the processor.</p></div></td></tr>';
    return;
  }}
  tbody.innerHTML = apps.map((a, i) => `
    <tr class="job-row" data-idx="${{i}}">
      <td class="company-cell">
        ${{a.linkedin_url ? `<a href="${{a.linkedin_url}}" target="_blank">${{a.company}}</a>` : a.company}}
        ${{a.domain ? `<div class="company-domain">${{a.domain}}</div>` : ''}}
      </td>
      <td>${{a.title}} ${{a.remote ? '<span class="remote-badge">Remote</span>' : ''}}</td>
      <td><span class="score-badge ${{scoreClass(a.score)}}">${{a.score !== null && a.score !== undefined ? a.score : '--'}}</span></td>
      <td><span class="status-pill status-${{a.status}}">${{STATUS_LABELS[a.status] || a.status}}</span></td>
      <td class="location-cell">${{a.location}}</td>
      <td class="location-cell">${{a.seniority}}</td>
      <td class="date-cell">${{formatDate(a.posted_on)}}</td>
    </tr>
    <tr class="detail-row" id="detail-${{i}}">
      <td colspan="7">
        <div class="detail-content">
          <div class="detail-grid">
            <div class="detail-section">
              <h4>Company Info</h4>
              <p>${{a.company}}${{a.domain ? ` &middot; ${{a.domain}}` : ''}}</p>
              <p>${{a.employee_count ? a.employee_count + ' employees' : ''}}${{a.founded ? ' &middot; Founded ' + a.founded : ''}}</p>
              ${{a.linkedin_url ? `<p><a href="${{a.linkedin_url}}" target="_blank" style="color:var(--purple)">View on LinkedIn</a></p>` : ''}}
            </div>
            <div class="detail-section">
              <h4>Application Status</h4>
              <p>CV Generated: ${{a.cv_generated ? 'Yes' : 'No'}}</p>
              <p>Cover Letter: ${{a.cover_letter_generated ? 'Yes' : 'No'}}</p>
              <p>Next Action: ${{a.next_action || 'None'}}</p>
            </div>
            <div class="detail-section">
              <h4>Timeline</h4>
              ${{(a.timeline||[]).map(t => `<div class="timeline-item"><span class="t-date">${{formatDate(t.date)}}</span> ${{t.notes || t.status}}</div>`).join('')}}
            </div>
          </div>
        </div>
      </td>
    </tr>
  `).join('');

  document.querySelectorAll('.job-row').forEach(row => {{
    row.addEventListener('click', () => {{
      const detail = document.getElementById('detail-' + row.dataset.idx);
      detail.classList.toggle('open');
    }});
  }});
}}

function renderKanban() {{
  const apps = getFilteredApps();
  const scroll = document.getElementById('kanbanScroll');
  const grouped = {{}};
  STATUSES_ORDER.forEach(s => grouped[s] = []);
  apps.forEach(a => {{
    if (grouped[a.status]) grouped[a.status].push(a);
    else {{ grouped['new'] = grouped['new'] || []; grouped['new'].push(a); }}
  }});

  scroll.innerHTML = STATUSES_ORDER
    .filter(s => grouped[s].length > 0)
    .map(s => `
      <div class="kanban-column">
        <div class="kanban-col-header">
          <span class="kanban-col-title">${{STATUS_LABELS[s]}}</span>
          <span class="kanban-col-count">${{grouped[s].length}}</span>
        </div>
        ${{grouped[s].map(a => `
          <div class="kanban-card">
            <div class="kanban-card-company">${{a.linkedin_url ? `<a href="${{a.linkedin_url}}" target="_blank">${{a.company}}</a>` : a.company}}</div>
            <div class="kanban-card-role">${{a.title}}</div>
            <div class="kanban-card-meta">
              <span class="kanban-card-location">${{a.location ? a.location.split(',')[0] : ''}}</span>
              <span class="score-badge ${{scoreClass(a.score)}}">${{a.score !== null && a.score !== undefined ? a.score : '--'}}</span>
            </div>
          </div>
        `).join('')}}
      </div>
    `).join('');
}}

function render() {{
  renderStats();
  renderTable();
  renderKanban();
}}

function setView(v) {{
  currentView = v;
  localStorage.setItem('jsearch-view', v);
  document.querySelectorAll('.view-btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  document.getElementById('tableView').style.display = v === 'table' ? 'block' : 'none';
  const kv = document.getElementById('kanbanView');
  kv.style.display = v === 'kanban' ? 'flex' : 'none';
  if (v === 'kanban') kv.classList.add('active');
  else kv.classList.remove('active');
}}

// Event Listeners
document.getElementById('searchInput').addEventListener('input', e => {{ currentSearch = e.target.value; render(); }});
document.getElementById('statusFilter').addEventListener('change', e => {{ currentStatusFilter = e.target.value; render(); }});
document.getElementById('sortSelect').addEventListener('change', e => {{ currentSort = e.target.value; render(); }});
document.querySelectorAll('.view-btn').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));

// Init
render();
setView(currentView);
</script>
</body>
</html>"""


def main():
    root = get_project_root()
    applications_dir = os.path.join(root, "applications")
    dashboard_dir = os.path.join(root, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)

    apps = collect_applications(applications_dir)
    stats = compute_stats(apps)
    html = generate_html(apps, stats)

    output_path = os.path.join(dashboard_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    print(f"  Total applications: {stats['total']}")
    print(f"  Analyzed: {stats['analyzed']}")
    print(f"  Applied: {stats['applied']}")
    print(f"  Avg Score: {stats['avg_score']}")


if __name__ == "__main__":
    main()
