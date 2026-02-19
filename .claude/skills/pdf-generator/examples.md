# PDF Generator Examples

This document provides practical examples of using the PDF generator skill.

## Example 1: Simple Text Document

Generate a basic PDF from plain text:

```bash
python scripts/generate_pdf.py "Welcome to PDF Generation!

This is a simple example of creating a PDF document from text.

You can include multiple paragraphs by separating them with blank lines." simple.pdf
```

**Output**: Creates `simple.pdf` with three paragraphs.

## Example 2: Meeting Notes

Create meeting notes PDF:

```bash
python scripts/generate_pdf.py "Team Standup - January 13, 2026

Attendees: Alice, Bob, Carol

Updates:
- Alice: Completed user authentication module
- Bob: Fixed critical bug in payment processing
- Carol: Started work on analytics dashboard

Action Items:
- Alice to review Bob's PR by EOD
- Carol to share analytics mockups tomorrow" meeting-notes.pdf "Team Standup Notes"
```

## Example 3: Report Generation

Generate a structured report:

```bash
python scripts/generate_pdf.py "Executive Summary

Our Q4 2025 performance exceeded expectations with a 25% increase in revenue.

Key Metrics:
Revenue: $2.5M (↑25%)
New Customers: 1,200 (↑40%)
Customer Retention: 92% (↑3%)

Challenges:
The rapid growth has put strain on our infrastructure. We need to invest in scaling.

Recommendations:
1. Hire 5 additional engineers
2. Upgrade server capacity
3. Implement automated testing

Conclusion:
With strategic investments, we're positioned for continued growth in 2026." q4-report.pdf "Q4 2025 Report"
```

## Example 4: Blog Post to PDF

Convert a blog post to PDF format:

```bash
python scripts/generate_pdf.py "10 Tips for Better Python Code

Python is a powerful language, but writing clean code requires discipline.

Tip 1: Use descriptive variable names
Instead of 'x' or 'temp', use names like 'user_count' or 'total_revenue'.

Tip 2: Follow PEP 8
Consistent formatting makes code readable. Use tools like black and ruff.

Tip 3: Write docstrings
Document your functions, classes, and modules. Future you will thank you.

Tip 4: Use type hints
Type hints catch bugs early and make code self-documenting.

Tip 5: Keep functions small
Each function should do one thing well.

Tip 6: Handle errors explicitly
Use try-except blocks and provide helpful error messages.

Tip 7: Write tests
Test-driven development catches bugs before they reach production.

Tip 8: Use virtual environments
Isolate project dependencies to avoid conflicts.

Tip 9: Review your own code
Before submitting, read your code as if seeing it for the first time.

Tip 10: Learn from others
Read open source code and adopt best practices." python-tips.pdf "10 Python Tips"
```

## Example 5: Documentation Export

Export documentation to PDF:

```bash
python scripts/generate_pdf.py "API Documentation

Authentication Endpoint

POST /api/auth/login
Request body: {\"username\": \"string\", \"password\": \"string\"}
Response: {\"token\": \"string\", \"expires_in\": 3600}

User Endpoints

GET /api/users
Returns list of all users. Requires authentication.

GET /api/users/{id}
Returns specific user by ID.

POST /api/users
Creates a new user. Requires admin role.

Error Codes

400 - Bad Request: Invalid input
401 - Unauthorized: Authentication required
403 - Forbidden: Insufficient permissions
404 - Not Found: Resource doesn't exist
500 - Internal Server Error: Server error occurred" api-docs.pdf "API Documentation"
```

## Example 6: Recipe Card

Create a recipe PDF:

```bash
python scripts/generate_pdf.py "Chocolate Chip Cookies

Prep time: 15 minutes
Cook time: 12 minutes
Servings: 24 cookies

Ingredients:
- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- 3/4 cup granulated sugar
- 3/4 cup packed brown sugar
- 2 large eggs
- 2 tsp vanilla extract
- 2 cups chocolate chips

Instructions:
1. Preheat oven to 375°F.
2. Mix flour, baking soda, and salt in a bowl.
3. Beat butter and sugars until creamy.
4. Add eggs and vanilla, beat well.
5. Gradually blend in flour mixture.
6. Stir in chocolate chips.
7. Drop rounded tablespoons onto baking sheets.
8. Bake 9-11 minutes until golden brown.
9. Cool on baking sheet for 2 minutes, then transfer to wire rack.

Tips:
- For chewier cookies, slightly underbake
- Refrigerate dough for 30 minutes for thicker cookies
- Use room temperature butter for best results" recipe.pdf "Chocolate Chip Cookies"
```

## Example 7: Todo List

Generate a todo list PDF:

```bash
python scripts/generate_pdf.py "Project Tasks - Week of Jan 13

High Priority:
□ Complete user authentication module
□ Fix critical payment bug
□ Deploy hotfix to production
□ Update API documentation

Medium Priority:
□ Review pull requests
□ Update test coverage
□ Refactor database queries
□ Optimize image loading

Low Priority:
□ Update README
□ Clean up old branches
□ Archive completed projects
□ Plan Q1 roadmap meeting

Notes:
Focus on high priority items first. Medium priority items can wait until next week if needed." tasks.pdf "Weekly Tasks"
```

## Example 8: Email to PDF

Convert email content to PDF:

```bash
python scripts/generate_pdf.py "From: alice@company.com
To: team@company.com
Date: January 13, 2026
Subject: Important Updates

Team,

I wanted to share some important updates regarding our upcoming product launch.

Launch Date:
We're targeting February 1st for the public release.

What's Ready:
- Core features are complete and tested
- Documentation is finalized
- Marketing materials are prepared

What's Pending:
- Final security audit (scheduled for next week)
- Load testing with 10k concurrent users
- App store submission

Next Steps:
1. Complete security audit by Jan 20
2. Conduct load tests Jan 21-22
3. Submit to app stores by Jan 23
4. Soft launch Jan 28 (beta users)
5. Public launch Feb 1

Let me know if you have any questions or concerns.

Best,
Alice" email-archive.pdf "Product Launch Email"
```

## Tips for Best Results

### Paragraph Formatting
- Use double newlines (`\n\n`) to separate paragraphs
- Single newlines within a paragraph will be converted to spaces

### Title Selection
- Choose descriptive titles that reflect the document content
- Titles appear centered at the top of the first page

### Content Organization
- Structure content with clear sections
- Use consistent formatting for similar elements
- Keep paragraphs reasonably sized (3-5 sentences)

### Special Characters
- Most Unicode characters are supported
- For special formatting, consider modifying the script

### File Naming
- Use descriptive file names: `q4-report.pdf` not `output.pdf`
- Avoid spaces in filenames (use hyphens or underscores)
- Include dates if generating regular reports: `report-2026-01-13.pdf`

## Automation Ideas

### Daily Reports
Create a cron job or scheduled task to generate daily reports:
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
python scripts/generate_pdf.py "$(cat daily-report.txt)" "reports/report-$DATE.pdf" "Daily Report $DATE"
```

### Email to PDF Archive
Archive important emails automatically:
```bash
python scripts/generate_pdf.py "$(cat email-content.txt)" "archive/$(date +%Y%m%d)-email.pdf"
```

### Batch Processing
Process multiple text files to PDFs:
```bash
for file in inputs/*.txt; do
    filename=$(basename "$file" .txt)
    python scripts/generate_pdf.py "$(cat $file)" "outputs/$filename.pdf" "$filename"
done
```

## Integration with Web APIs

You can combine this skill with web APIs to generate PDFs from online content:

```bash
# Fetch content from API and generate PDF
curl -s https://api.example.com/content | python scripts/generate_pdf.py "$(cat)" api-content.pdf
```

## Next Steps

- Try modifying `scripts/generate_pdf.py` to add custom formatting
- Read `reference.md` for advanced reportlab features
- Experiment with different text structures and layouts
