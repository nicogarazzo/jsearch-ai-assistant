#!/usr/bin/env python3
"""
JSearch PDF Generator
Converts cv.md and cover-letter.md to styled PDFs.
Usage:
  python3 scripts/generate_pdf.py                     # All applications with cv.md
  python3 scripts/generate_pdf.py canonical            # Specific folder (partial match)
  python3 scripts/generate_pdf.py --cover-letters      # Also generate cover letter PDFs
Run from the jsearch/ project root.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_project_root, load_yaml, slugify

# LaTeX header for professional CV styling
LATEX_HEADER = r"""
\usepackage{enumitem}
\setlist[itemize]{nosep, left=0pt}
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries\color[HTML]{2d2d2d}}{}{0em}{}[\titlerule]
\titleformat{\subsection}{\normalsize\bfseries}{}{0em}{}
\titlespacing*{\section}{0pt}{14pt}{6pt}
\titlespacing*{\subsection}{0pt}{10pt}{4pt}
\usepackage{parskip}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\pagestyle{empty}
"""


def find_applications(apps_dir, query=None):
    """Find application folders, optionally filtered by partial name match."""
    folders = []
    if not os.path.exists(apps_dir):
        return folders
    for f in sorted(os.listdir(apps_dir)):
        if not os.path.isdir(os.path.join(apps_dir, f)):
            continue
        if query and query.lower() not in f.lower():
            continue
        folders.append(f)
    return folders


def generate_pdf(md_path, pdf_path, title="CV"):
    """Convert a markdown file to PDF using pandoc + xelatex."""
    if not os.path.exists(md_path):
        return False

    # Write temporary header file
    header_path = md_path + ".header.tex"
    with open(header_path, "w") as f:
        f.write(LATEX_HEADER)

    cmd = [
        "pandoc", md_path,
        "-o", pdf_path,
        "--pdf-engine=xelatex",
        "-V", "geometry:margin=0.85in",
        "-V", "mainfont=Helvetica Neue",
        "-V", "monofont=Menlo",
        "-V", "fontsize=10.5pt",
        "-V", "linestretch=1.15",
        "-V", "colorlinks=true",
        "-V", "linkcolor=NavyBlue",
        "-V", "urlcolor=NavyBlue",
        "-H", header_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Cleanup header
    if os.path.exists(header_path):
        os.remove(header_path)

    if result.returncode != 0:
        print(f"    ERROR generating {title}: {result.stderr[:200]}")
        return False
    return True


def main():
    root = get_project_root()
    apps_dir = os.path.join(root, "applications")
    include_cover = "--cover-letters" in sys.argv

    # Parse query (first non-flag argument)
    query = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            query = arg
            break

    folders = find_applications(apps_dir, query)
    if not folders:
        print("No matching application folders found.")
        return

    # Filenames carry the applicant's name so recruiters can find the file later
    profile = load_yaml(os.path.join(root, "config", "profile.yaml"))
    owner = "".join(w.capitalize() for w in slugify(profile.get("name") or "Candidate").split("-")) or "Candidate"

    generated = 0
    skipped = 0

    for folder in folders:
        folder_path = os.path.join(apps_dir, folder)
        cv_md = os.path.join(folder_path, "cv.md")
        cl_md = os.path.join(folder_path, "cover-letter.md")

        if not os.path.exists(cv_md):
            continue

        # Load job data for filename
        job = load_yaml(os.path.join(folder_path, "job.yaml"))
        company = (job.get("company") or {}).get("name", "Unknown")
        role = (job.get("role") or {}).get("title", "Unknown")
        safe_company = company.replace(" ", "-").replace("/", "-")[:30]

        print(f"\n  {company} - {role}")

        # Generate CV PDF
        cv_pdf = os.path.join(folder_path, f"CV_{owner}_{safe_company}.pdf")
        if generate_pdf(cv_md, cv_pdf, "CV"):
            print(f"    CV PDF: {os.path.basename(cv_pdf)}")
            generated += 1
        else:
            skipped += 1

        # Generate Cover Letter PDF
        if include_cover and os.path.exists(cl_md):
            cl_pdf = os.path.join(folder_path, f"CoverLetter_{owner}_{safe_company}.pdf")
            if generate_pdf(cl_md, cl_pdf, "Cover Letter"):
                print(f"    Cover Letter PDF: {os.path.basename(cl_pdf)}")
                generated += 1

    print(f"\nDone. Generated {generated} PDFs, {skipped} errors.")


if __name__ == "__main__":
    main()
