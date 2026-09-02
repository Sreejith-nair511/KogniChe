"""
NEXORA Design Submission — PDF Compiler
Concatenates all 22 markdown documents in order, renders diagrams,
and compiles to a single PDF.

Requirements (choose one):
  pip install markdown weasyprint         ← best quality
  pip install markdown pdfkit             ← requires wkhtmltopdf installed
  pip install pandoc                      ← requires pandoc + pdflatex/wkhtmltopdf

Usage:
  python compile_submission.py            ← auto-selects best available method
  python compile_submission.py --method weasyprint
  python compile_submission.py --method pdfkit
  python compile_submission.py --method pandoc
  python compile_submission.py --html-only   ← outputs HTML only (for browser print-to-PDF)
"""

import os
import sys
import re
import argparse
import subprocess
from pathlib import Path

SUBMISSION_DIR = Path(__file__).parent
OUTPUT_DIR = SUBMISSION_DIR.parent
OUTPUT_PDF = OUTPUT_DIR / "NEXORA_APS-04_Design_Submission.pdf"
OUTPUT_HTML = SUBMISSION_DIR / "NEXORA_combined.html"
COMBINED_MD = SUBMISSION_DIR / "NEXORA_combined.md"
CSS_PATH = SUBMISSION_DIR / "assets" / "style.css"

# Ordered file list
DOCUMENTS = [
    "00_COVER.md",
    "01_EXECUTIVE_SUMMARY.md",
    "02_PROBLEM_UNDERSTANDING.md",
    "03_SCOPE_AND_NON_SCOPE.md",
    "04_USER_JOURNEY.md",
    "05_SOLUTION_OVERVIEW.md",
    "06_ARCHITECTURE.md",
    "07_SYSTEM_FLOW.md",
    "08_AI_FEATURES_AND_GROUNDING.md",
    "09_HYBRID_RETRIEVAL.md",
    "10_PERSONALIZATION_AND_RERANKING.md",
    "11_COLD_START_AND_SESSION_LEARNING.md",
    "12_MULTILINGUAL_INTELLIGENCE.md",
    "13_EXPLAINABILITY.md",
    "14_DATASET_AND_DATA_USAGE.md",
    "15_EVALUATION_STRATEGY.md",
    "16_BUSINESS_BENEFITS.md",
    "17_TECH_STACK.md",
    "18_24_HOUR_EXECUTION_PLAN.md",
    "19_RISKS_AND_FALLBACKS.md",
    "20_MVP_ACCEPTANCE_CRITERIA.md",
    "21_FINAL_DEMO_FLOW.md",
    "22_CONCLUSION.md",
]


def concatenate_markdown() -> str:
    """Join all documents with consistent section separators."""
    parts = []
    for fname in DOCUMENTS:
        path = SUBMISSION_DIR / fname
        if not path.exists():
            print(f"  WARNING: {fname} not found — skipping")
            continue
        content = path.read_text(encoding="utf-8")
        # Strip leading/trailing whitespace
        content = content.strip()
        parts.append(content)
    # Join with page-break marker
    return "\n\n---\n\n".join(parts)


def render_mermaid_to_png():
    """Attempt to render .mmd diagrams to PNG using mermaid-cli."""
    diagrams_dir = SUBMISSION_DIR / "assets" / "diagrams"
    for mmd_file in diagrams_dir.glob("*.mmd"):
        png_file = mmd_file.with_suffix(".png")
        if png_file.exists():
            print(f"  Diagram already rendered: {png_file.name}")
            continue
        try:
            result = subprocess.run(
                ["mmdc", "-i", str(mmd_file), "-o", str(png_file),
                 "-t", "dark", "-b", "transparent", "-w", "1400"],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                print(f"  Rendered: {png_file.name}")
            else:
                print(f"  mmdc failed for {mmd_file.name}: {result.stderr.decode()[:100]}")
        except FileNotFoundError:
            print("  mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli")
        except subprocess.TimeoutExpired:
            print(f"  mmdc timed out for {mmd_file.name}")


def inject_diagram_images(md_content: str) -> str:
    """Replace mermaid code blocks with rendered PNG references if available."""
    diagrams_dir = SUBMISSION_DIR / "assets" / "diagrams"

    diagram_counter = {"n": 0}

    def replace_mermaid(match):
        code = match.group(1).strip()
        diagram_counter["n"] += 1
        # Identify diagram by content keywords
        code_lower = code.lower()
        if "frontend" in code_lower and "fastapi" in code_lower:
            png = diagrams_dir / "architecture.png"
            label = "System Architecture — NEXORA"
        elif "user query" in code_lower and "language detection" in code_lower:
            png = diagrams_dir / "system_flow.png"
            label = "Search Pipeline — System Flow"
        elif "user action" in code_lower and "feedback loop" in code_lower.replace("\n", " "):
            png = diagrams_dir / "feedback_loop.png"
            label = "Interaction Feedback Loop"
        elif "store interaction" in code_lower or "interactionresponse" in code_lower:
            png = diagrams_dir / "feedback_loop.png"
            label = "Interaction Feedback Loop"
        else:
            png = None
            label = f"Diagram {diagram_counter['n']}"

        if png and png.exists():
            rel_path = os.path.relpath(png, SUBMISSION_DIR)
            return f'\n![{label}]({rel_path.replace(chr(92), "/")})\n'
        # Keep as fenced code block if no PNG
        return match.group(0)

    # Replace ```mermaid ... ``` blocks
    return re.sub(r"```mermaid\n(.*?)```", replace_mermaid, md_content, flags=re.DOTALL)


def build_html(md_content: str) -> str:
    """Convert markdown to a complete styled HTML document."""
    try:
        import markdown
        from markdown.extensions.tables import TableExtension
        from markdown.extensions.fenced_code import FencedCodeExtension
        from markdown.extensions.toc import TocExtension
    except ImportError:
        print("ERROR: pip install markdown")
        sys.exit(1)

    css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""

    html_body = markdown.markdown(
        md_content,
        extensions=[
            TableExtension(),
            FencedCodeExtension(),
            TocExtension(toc_depth="1-3"),
            "attr_list",
            "def_list",
            "abbr",
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NEXORA — APS-04 Design Submission</title>
  <style>
{css}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


def compile_weasyprint(html: str):
    """Render HTML → PDF using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
        print("  Using WeasyPrint...")
        HTML(string=html, base_url=str(SUBMISSION_DIR)).write_pdf(
            str(OUTPUT_PDF),
            stylesheets=[CSS(string="@page { margin: 20mm 22mm; }")]
        )
        print(f"  PDF written: {OUTPUT_PDF}")
        return True
    except ImportError:
        print("  WeasyPrint not installed. pip install weasyprint")
        return False
    except Exception as e:
        print(f"  WeasyPrint error: {e}")
        return False


def compile_pdfkit(html_path: Path):
    """Render HTML → PDF using pdfkit (requires wkhtmltopdf)."""
    try:
        import pdfkit
        print("  Using pdfkit / wkhtmltopdf...")
        options = {
            "page-size": "A4",
            "margin-top": "20mm",
            "margin-bottom": "20mm",
            "margin-left": "22mm",
            "margin-right": "22mm",
            "encoding": "UTF-8",
            "enable-local-file-access": "",
            "quiet": "",
        }
        pdfkit.from_file(str(html_path), str(OUTPUT_PDF), options=options)
        print(f"  PDF written: {OUTPUT_PDF}")
        return True
    except ImportError:
        print("  pdfkit not installed. pip install pdfkit")
        return False
    except Exception as e:
        print(f"  pdfkit error: {e}")
        return False


def compile_pandoc():
    """Use pandoc CLI to produce PDF."""
    print("  Using pandoc...")
    doc_paths = [str(SUBMISSION_DIR / f) for f in DOCUMENTS if (SUBMISSION_DIR / f).exists()]
    cmd = [
        "pandoc", *doc_paths,
        "-o", str(OUTPUT_PDF),
        "--metadata", "title=NEXORA APS-04 Design Submission",
        "--toc", "--toc-depth=2",
        "-V", "geometry:margin=20mm",
        "-V", "fontsize=10pt",
        "--pdf-engine=wkhtmltopdf",
    ]
    if CSS_PATH.exists():
        cmd += ["--css", str(CSS_PATH)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            print(f"  PDF written: {OUTPUT_PDF}")
            return True
        print(f"  pandoc error: {result.stderr.decode()[:300]}")
        return False
    except FileNotFoundError:
        print("  pandoc not found. Install from https://pandoc.org")
        return False
    except subprocess.TimeoutExpired:
        print("  pandoc timed out")
        return False


def verify_pdf():
    """Basic size and existence check."""
    if not OUTPUT_PDF.exists():
        print(f"\n  ERROR: PDF not created at {OUTPUT_PDF}")
        return False
    size_mb = OUTPUT_PDF.stat().st_size / (1024 * 1024)
    print(f"\n  PDF size: {size_mb:.1f} MB")
    if size_mb > 25:
        print("  WARNING: PDF exceeds 25 MB limit. Compress images and try again.")
        return False
    print(f"  OK: {OUTPUT_PDF.name} ({size_mb:.1f} MB) — ready for submission")
    return True


def main():
    parser = argparse.ArgumentParser(description="Compile NEXORA submission to PDF")
    parser.add_argument("--method", choices=["weasyprint", "pdfkit", "pandoc", "auto"], default="auto")
    parser.add_argument("--html-only", action="store_true", help="Output HTML only")
    args = parser.parse_args()

    print("=" * 60)
    print("NEXORA Design Submission Compiler")
    print("=" * 60)

    # Step 1: render diagrams
    print("\n[1/4] Rendering diagrams...")
    render_mermaid_to_png()

    # Step 2: concatenate markdown
    print("\n[2/4] Concatenating documents...")
    md = concatenate_markdown()
    md = inject_diagram_images(md)
    COMBINED_MD.write_text(md, encoding="utf-8")
    print(f"  Combined markdown: {COMBINED_MD.name} ({len(md):,} chars)")

    # Step 3: build HTML
    print("\n[3/4] Building HTML...")
    html = build_html(md)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  HTML written: {OUTPUT_HTML.name}")

    if args.html_only:
        print(f"\n  HTML-only mode. Open {OUTPUT_HTML} in browser → Print → Save as PDF")
        return

    # Step 4: compile PDF
    print(f"\n[4/4] Compiling PDF -> {OUTPUT_PDF.name}...")
    success = False

    if args.method == "weasyprint":
        success = compile_weasyprint(html)
    elif args.method == "pdfkit":
        success = compile_pdfkit(OUTPUT_HTML)
    elif args.method == "pandoc":
        success = compile_pandoc()
    else:  # auto
        # Try each in order of preference
        success = (
            compile_weasyprint(html) or
            compile_pandoc() or
            compile_pdfkit(OUTPUT_HTML)
        )
        if not success:
            print("\n  No PDF engine available. Try:")
            print("    pip install weasyprint")
            print("    pip install markdown")
            print(f"\n  Fallback: open {OUTPUT_HTML} in a browser and print to PDF.")

    if success:
        verify_pdf()

    print("\n" + "=" * 60)
    print("Done. Review SUBMISSION_CHECKLIST.md before uploading.")
    print("=" * 60)


if __name__ == "__main__":
    main()
