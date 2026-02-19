---
name: pdf-generator
description: Generate PDF documents from text descriptions using Python's reportlab library. Use when working with PDF files, creating documents, converting text to PDF, generating reports, or when the user mentions PDFs, document generation, reports, or exportable formats.
allowed-tools:
  - Bash
  - Read
  - Write
model: claude-opus-4-5-20251101
context: inherit
user-invocable: true
# OmniForge-specific extensions (not in Claude Code standard):
priority: 0
tags:
  - pdf
  - document-generation
  - python
---

# PDF Generator Skill

Generate professional PDF documents from text descriptions using Python's reportlab library.

## Overview

This skill enables you to create PDF documents programmatically from text input. It supports:
- Multi-paragraph text formatting
- Custom titles and metadata
- Automatic page breaks
- Standard PDF formatting (letter size, readable fonts)

## Usage

To generate a PDF, follow these steps:

1. **Prepare your text description**: Have the text content you want to convert to PDF
2. **Execute the generation script**: Run the Python script with your text
3. **Retrieve the PDF**: The PDF will be saved to your specified output path

## Quick Start

```bash
python scripts/generate_pdf.py "Your text content here" output.pdf
```

## Script Parameters

The `generate_pdf.py` script accepts:
- **arg1**: Text content (required) - The text to include in the PDF
- **arg2**: Output path (required) - Where to save the PDF file
- **arg3**: Title (optional) - PDF title (default: "Generated Document")

## Example Usage

### Basic PDF Generation

```bash
python scripts/generate_pdf.py "This is a simple PDF document." output.pdf
```

### PDF with Custom Title

```bash
python scripts/generate_pdf.py "Quarterly report content..." report.pdf "Q4 2025 Report"
```

### Multi-paragraph Content

```bash
python scripts/generate_pdf.py "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3." document.pdf
```

## Requirements

The script requires the `reportlab` Python package:

```bash
pip install reportlab
```

## Output Format

Generated PDFs have:
- Letter size (8.5" x 11")
- 1-inch margins
- 12pt Helvetica font for body text
- 16pt Helvetica-Bold for titles
- Automatic page breaks for long content

## Advanced Usage

For more control over PDF generation, you can:
1. Read [reference.md](reference.md) for reportlab documentation
2. Modify the generation script in `scripts/generate_pdf.py`
3. Add custom fonts, images, or formatting

## Troubleshooting

**Error: reportlab not found**
- Solution: Install reportlab with `pip install reportlab`

**Error: Permission denied**
- Solution: Ensure you have write permissions for the output directory

**PDF looks cut off**
- Solution: Long paragraphs are automatically wrapped. For very long text, consider breaking into sections.

## Technical Details

- **Script location**: `scripts/generate_pdf.py`
- **Dependencies**: reportlab >= 4.0.0
- **Python version**: 3.9+
- **Output format**: PDF 1.4 compatible with all readers

## See Also

- [reference.md](reference.md) - Reportlab API documentation
- [examples.md](examples.md) - More PDF generation examples
