"""
NEXORA Submission PDF Generator — uses Playwright (Chromium headless)
Produces a high-quality, properly-styled PDF from the compiled HTML.

Usage:
    python generate_pdf.py

Output:
    docs/NEXORA_APS-04_Design_Submission.pdf
"""
import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SUBMISSION_DIR = Path(__file__).parent
HTML_PATH = SUBMISSION_DIR / "NEXORA_combined.html"
OUTPUT_PDF = SUBMISSION_DIR.parent / "NEXORA_APS-04_Design_Submission.pdf"
DIAGRAMS_DIR = SUBMISSION_DIR / "assets" / "diagrams"


def render_diagrams_playwright():
    """Render .mmd diagrams to PNG using a small inline Node.js call if mmdc available."""
    for mmd_file in DIAGRAMS_DIR.glob("*.mmd"):
        png_file = mmd_file.with_suffix(".png")
        if png_file.exists():
            print(f"  Diagram cached: {png_file.name}")
            continue
        # Try mmdc
        import subprocess
        try:
            r = subprocess.run(
                ["mmdc", "-i", str(mmd_file), "-o", str(png_file),
                 "-t", "dark", "-b", "#0d1321", "-w", "1400"],
                capture_output=True, timeout=30
            )
            if r.returncode == 0:
                print(f"  Diagram rendered: {png_file.name}")
            else:
                print(f"  mmdc unavailable for {mmd_file.name} — diagram will show as code block")
        except FileNotFoundError:
            print(f"  mmdc not installed — {mmd_file.name} will show as code block")
        except Exception as e:
            print(f"  Diagram render skipped: {e}")


def patch_html_for_pdf(html_path: Path) -> str:
    """Read the HTML and inject PDF-specific overrides: page breaks, print CSS."""
    html = html_path.read_text(encoding="utf-8")

    # Inject print-mode PDF enhancements at end of <head>
    pdf_css = """
    <style>
    /* PDF-specific overrides */
    @page {
      size: A4;
      margin: 20mm 22mm 20mm 22mm;
    }

    /* Section dividers become page breaks */
    hr { page-break-after: always; border: none; }

    /* Don't break tables or code blocks mid-page */
    table, pre, blockquote, figure { page-break-inside: avoid; }

    /* Keep headings with their first paragraph */
    h1, h2, h3 { page-break-after: avoid; }

    /* Cover page — generous top margin */
    body > h1:first-of-type {
      margin-top: 60px !important;
      font-size: 32pt !important;
    }

    /* Light mode for PDF readability */
    body {
      background: #ffffff !important;
      color: #0d1321 !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    h1 { color: #0d1321 !important; border-color: #0d7a5f !important; }
    h2 { color: #0d7a5f !important; }
    h3 { color: #1a2744 !important; }
    p, li, td { color: #1e293b !important; }

    strong { color: #0d1321 !important; }
    em { color: #0d7a5f !important; }
    code { background: #f1f5f9 !important; color: #0d7a5f !important; }
    pre { background: #f1f5f9 !important; border-color: #0d7a5f !important; color: #1e293b !important; }

    table { background: #ffffff !important; border: 1px solid #e2e8f0 !important; }
    thead tr { background: #f0faf6 !important; }
    thead th { color: #0d7a5f !important; }
    tbody tr { border-color: #e2e8f0 !important; }
    tbody td { color: #1e293b !important; }
    tbody tr:nth-child(even) { background: #f8fafc !important; }

    blockquote {
      background: #f8fafc !important;
      border-color: #0d7a5f !important;
      color: #334155 !important;
    }
    blockquote p { color: #334155 !important; }

    a { color: #0d7a5f !important; }

    /* Metric table highlight */
    tbody tr:has(td strong) { background: #f0faf6 !important; }

    /* Footer watermark */
    @page {
      @bottom-center {
        content: "NEXORA - APS-04 - Kognivera Hackathon 2026";
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: #94a3b8;
      }
      @bottom-right {
        content: counter(page);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: #94a3b8;
      }
    }
    </style>
    """

    # Insert before </head>
    html = html.replace("</head>", pdf_css + "\n</head>")
    return html


def generate_pdf_playwright():
    """Use Playwright's Chromium to render the HTML to PDF."""
    from playwright.sync_api import sync_playwright

    # Write patched HTML to a temp file
    patched_html = patch_html_for_pdf(HTML_PATH)
    patched_path = SUBMISSION_DIR / "NEXORA_print.html"
    patched_path.write_text(patched_html, encoding="utf-8")

    print(f"  Launching Chromium headless...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Load the HTML file
        file_url = patched_path.as_uri()
        page.goto(file_url, wait_until="networkidle", timeout=30000)

        # Wait for any fonts / images to load
        page.wait_for_timeout(1500)

        # Generate PDF
        page.pdf(
            path=str(OUTPUT_PDF),
            format="A4",
            margin={
                "top": "20mm",
                "bottom": "20mm",
                "left": "22mm",
                "right": "22mm",
            },
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template="""
              <div style="font-size:8px; color:#94a3b8; width:100%; padding:0 22mm;
                          display:flex; justify-content:space-between;">
                <span>NEXORA — APS-04 — Kognivera Hackathon 2026</span>
                <span><span class="pageNumber"></span></span>
              </div>
            """,
        )
        browser.close()

    # Clean up temp file
    patched_path.unlink(missing_ok=True)


def verify():
    if not OUTPUT_PDF.exists():
        print(f"\n  ERROR: PDF not created at {OUTPUT_PDF}")
        return False
    size_mb = OUTPUT_PDF.stat().st_size / (1024 * 1024)
    print(f"\n  PDF: {OUTPUT_PDF.name}")
    print(f"  Size: {size_mb:.2f} MB")
    if size_mb > 25:
        print("  WARNING: exceeds 25 MB limit — consider compressing images")
    else:
        print("  OK: ready for submission")
    return True


def main():
    print("=" * 60)
    print("NEXORA PDF Generator (Playwright / Chromium)")
    print("=" * 60)

    # Ensure HTML exists
    if not HTML_PATH.exists():
        print(f"\nHTML not found: {HTML_PATH}")
        print("Run compile_submission.py first (--html-only is fine):")
        print("  python compile_submission.py --html-only")
        sys.exit(1)

    # Try to render diagrams
    print("\n[1/3] Rendering diagrams...")
    render_diagrams_playwright()

    # Ensure Playwright browsers are installed
    print("\n[2/3] Checking Playwright browser...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # This will raise if chromium isn't installed
            try:
                p.chromium.launch().close()
                print("  Chromium: ready")
            except Exception:
                print("  Chromium not installed. Running: playwright install chromium")
                import subprocess
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                               check=True, timeout=300)
                print("  Chromium installed.")
    except ImportError:
        print("  playwright not available")
        sys.exit(1)

    # Generate PDF
    print(f"\n[3/3] Generating PDF -> {OUTPUT_PDF.name}...")
    generate_pdf_playwright()

    verify()
    print("\n" + "=" * 60)
    print("Done. Check SUBMISSION_CHECKLIST.md before uploading.")
    print("=" * 60)


if __name__ == "__main__":
    main()
