# PDF Generator Reference Documentation

## Reportlab Library Overview

Reportlab is a powerful Python library for generating PDF documents programmatically. This reference covers the key concepts used in the PDF generator skill.

## Key Concepts

### Document Structure

A PDF document consists of:
1. **Document Template** - Defines page size, margins, and layout
2. **Story** - List of flowable elements (paragraphs, images, etc.)
3. **Styles** - Define text formatting (fonts, sizes, colors)

### Page Sizes

Common page sizes available in reportlab:
- `letter` - US Letter (8.5" × 11")
- `A4` - International standard (210mm × 297mm)
- `legal` - US Legal (8.5" × 14")

### Text Formatting

#### Paragraph Styles

Paragraph styles control:
- Font family and size
- Text color
- Alignment (left, center, right, justify)
- Spacing (before, after, line height)
- Indentation

#### Available Fonts

Standard PDF fonts:
- Helvetica (sans-serif)
- Times (serif)
- Courier (monospace)

### Flowable Elements

Elements that can be added to the story:

#### Paragraph
```python
from reportlab.platypus import Paragraph
para = Paragraph("Text content", style)
```

#### Spacer
```python
from reportlab.platypus import Spacer
from reportlab.lib.units import inch
spacer = Spacer(1, 0.5 * inch)  # 0.5 inch vertical space
```

#### Image
```python
from reportlab.platypus import Image
img = Image("image.jpg", width=4*inch, height=3*inch)
```

#### Table
```python
from reportlab.platypus import Table
data = [['Name', 'Age'], ['Alice', '30'], ['Bob', '25']]
table = Table(data)
```

## API Reference

### SimpleDocTemplate

Constructor:
```python
SimpleDocTemplate(
    filename,              # Output file path
    pagesize=letter,       # Page size tuple (width, height)
    rightMargin=72,        # Right margin in points (72 = 1 inch)
    leftMargin=72,         # Left margin in points
    topMargin=72,          # Top margin in points
    bottomMargin=18,       # Bottom margin in points
)
```

Methods:
- `build(story)` - Generate the PDF from story elements

### Paragraph

Constructor:
```python
Paragraph(text, style, bulletText=None)
```

Parameters:
- `text` - String content (supports basic HTML-like tags)
- `style` - ParagraphStyle object
- `bulletText` - Optional bullet character

### ParagraphStyle

Create custom styles:
```python
from reportlab.lib.styles import ParagraphStyle

style = ParagraphStyle(
    name='CustomStyle',
    fontName='Helvetica',
    fontSize=12,
    leading=14,           # Line height
    textColor='black',
    alignment=0,          # 0=left, 1=center, 2=right, 4=justify
    spaceAfter=6,        # Space after paragraph in points
    spaceBefore=0,       # Space before paragraph in points
)
```

## HTML-like Tags in Paragraphs

Supported tags:
- `<b>bold</b>` - Bold text
- `<i>italic</i>` - Italic text
- `<u>underline</u>` - Underlined text
- `<font color="red">colored</font>` - Colored text
- `<br/>` - Line break

Example:
```python
text = "This is <b>bold</b> and <i>italic</i> text."
para = Paragraph(text, normal_style)
```

## Units and Measurements

Reportlab uses points (1/72 inch) as the base unit:

```python
from reportlab.lib.units import inch, cm, mm

# Convert to points
width = 5 * inch     # 5 inches = 360 points
height = 10 * cm     # 10 centimeters
margin = 25 * mm     # 25 millimeters
```

## Error Handling

Common errors and solutions:

### ImportError: No module named 'reportlab'
**Solution**: Install reportlab
```bash
pip install reportlab
```

### IOError: [Errno 13] Permission denied
**Solution**: Check write permissions or change output path
```bash
chmod 755 output_directory
```

### ValueError: Invalid page size
**Solution**: Use valid page size tuple (width, height) in points
```python
from reportlab.lib.pagesizes import letter
pagesize = letter  # Or (612, 792) for letter size
```

## Performance Tips

1. **Reuse styles** - Create styles once, reuse for multiple paragraphs
2. **Large documents** - For very large PDFs (1000+ pages), use `BaseDocTemplate` for more control
3. **Images** - Compress images before adding to reduce file size
4. **Fonts** - Stick to standard fonts to avoid embedding custom fonts

## Advanced Topics

### Custom Fonts

To use custom TrueType fonts:
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('CustomFont', 'font.ttf'))
```

### Page Numbers

Add page numbers using PageTemplate:
```python
from reportlab.platypus import PageTemplate, Frame

def add_page_number(canvas, doc):
    canvas.drawString(300, 30, f"Page {doc.page}")
```

### Watermarks

Add watermarks to every page:
```python
def add_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 60)
    canvas.setFillGray(0.9)
    canvas.drawString(100, 400, "DRAFT")
    canvas.restoreState()
```

## See Also

- Official Reportlab documentation: https://www.reportlab.com/docs/
- PyPI package: https://pypi.org/project/reportlab/
- User guide: https://www.reportlab.com/docs/reportlab-userguide.pdf
