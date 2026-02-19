#!/usr/bin/env python3
"""Generate PDF from text description.

This script creates a PDF document from text input using reportlab.
"""

import sys
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
except ImportError:
    print("Error: reportlab is not installed", file=sys.stderr)
    print("Install with: pip install reportlab", file=sys.stderr)
    sys.exit(1)


def create_pdf(text: str, output_path: str, title: str = "Generated Document") -> None:
    """Create a PDF from text content.

    Args:
        text: Text content to include in PDF
        output_path: Path where PDF should be saved
        title: Document title (default: "Generated Document")
    """
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Create PDF document
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=72,  # 1 inch
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Container for document elements
    story = []

    # Get default styles
    styles = getSampleStyleSheet()

    # Add custom title style
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor="black",
        spaceAfter=30,
        alignment=1,  # Center
    )

    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Split text into paragraphs
    paragraphs = text.split("\n\n")

    # Add each paragraph
    for para_text in paragraphs:
        if para_text.strip():
            # Replace single newlines with spaces, keep double newlines as paragraph breaks
            para_text = para_text.replace("\n", " ")
            story.append(Paragraph(para_text, styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {output_path}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: generate_pdf.py <text> <output_path> [title]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Arguments:", file=sys.stderr)
        print("  text         - Text content to convert to PDF", file=sys.stderr)
        print("  output_path  - Output PDF file path", file=sys.stderr)
        print("  title        - Optional document title (default: 'Generated Document')", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print('  generate_pdf.py "Hello, World!" output.pdf "My Document"', file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    output_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "Generated Document"

    try:
        create_pdf(text, output_path, title)
    except Exception as e:
        print(f"Error creating PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
