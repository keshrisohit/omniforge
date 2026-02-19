---
name: summarizing-google-docs
description: Creates concise summaries of Google Docs by extracting key points, main ideas, and essential information. Use when you need to quickly understand lengthy documents, share critical information with others, or create executive summaries for reports and project documents.
---
# summarizing-google-docs

## Quick start

Use this skill when you need to quickly understand lengthy Google Docs, share critical information with others, or create executive summaries for reports and project documents.

## Core workflow

Follow this step-by-step process to create effective summaries:

1. **Access the document** - Use the provided Google Doc link or ID to retrieve the content
2. **Analyze structure** - Identify document type, sections, and key organizational elements
3. **Extract key information** - Pull out main points, important details, and critical data
4. **Generate summary** - Create concise output matching the document's purpose and audience
5. **Format appropriately** - Present summary in the requested format (new doc, section, or text)

## Instructions

### Step 1: Document Access
- Use the Google Docs API to retrieve document content
- Handle both direct links and document IDs
- Ensure proper authentication and permissions

### Step 2: Content Analysis
- Identify document type (meeting notes, research paper, project plan, etc.)
- Locate key sections and structural elements
- Determine the document's purpose and intended audience

### Step 3: Information Extraction
- Extract main ideas from each section
- Identify critical data points and statistics
- Note important relationships and connections
- Capture action items, decisions, or conclusions

### Step 4: Summary Generation
- Condense information while preserving essential meaning
- Maintain logical flow and coherence
- Use appropriate terminology for the document type
- Keep summaries concise (typically 3-5 paragraphs)

### Step 5: Output Formatting
- Create new Google Doc for the summary if requested
- Add summary as new section if specified
- Return text response for immediate use
- Include proper formatting and structure

## Examples

### Meeting Notes (10-page document)
**Input:** Meeting notes with action items, decisions, and key discussions
**Output:** 3-paragraph summary highlighting:
- Decisions made and their implications
- Action items assigned with owners and deadlines
- Main discussion points and key takeaways

### Research Paper (15-page document)
**Input:** Research paper with methodology, results, and conclusions
**Output:** Abstract-style summary capturing:
- Research question and objectives
- Methodology overview
- Key findings and results
- Conclusions and implications

### Project Plan (5-page document)
**Input:** Project plan with timelines, milestones, and responsibilities
**Output:** Executive summary listing:
- Project objectives and scope
- Key milestones and deliverables
- Timeline overview and critical dates
- Responsible parties and stakeholders

## Edge cases and special considerations

### Handling Different Document Types
- **Technical documents:** Focus on methodology, results, and implications
- **Meeting notes:** Emphasize decisions, action items, and key discussions
- **Project plans:** Highlight objectives, milestones, and responsibilities
- **Reports:** Capture main findings, recommendations, and next steps

### Length Management
- Aim for 10-15% of original document length
- Never exceed 3-5 paragraphs for most summaries
- Adjust based on document complexity and purpose

### Content Prioritization
- Decisions and action items always take priority
- Key findings and conclusions are essential
- Supporting details can be condensed or omitted
- Examples and illustrations may be summarized briefly

### Formatting Guidelines
- Use clear paragraph breaks between main ideas
- Maintain logical flow from introduction to conclusion
- Include bullet points for lists of items when appropriate
- Preserve key terminology and technical terms

## Validation checklist

Before delivering the summary:
- [ ] All key points from original document are captured
- [ ] Summary is appropriately concise (10-15% of original)
- [ ] Main ideas are clearly presented and logically organized
- [ ] Important terminology and context are preserved
- [ ] Format matches the requested output type
- [ ] No critical information has been omitted or misrepresented

## File operations

- Read the source Google Doc using the provided link or ID
- Create new documents in the same folder when requested
- Add summary sections to existing documents if specified
- Handle permissions and sharing settings appropriately

## Script execution

Use the following script structure for Google Docs operations:
```bash
python {{baseDir}}/scripts/google_docs_summary.py \
  --document-id DOC_ID \
  --output-format [new_doc|section|text] \
  --summary-length [short|medium|long]
```

## Common pitfalls to avoid

- Don't include excessive detail or verbatim text
- Avoid introducing personal interpretation or bias
- Don't omit critical decisions or action items
- Avoid changing the original meaning or context
- Don't create summaries that are too long or too short
- Avoid technical jargon when summarizing for non-technical audiences

## Performance considerations

- Process documents efficiently to handle large files
- Cache frequently accessed documents when appropriate
- Use batch operations for multiple document processing
- Monitor API usage limits and implement appropriate delays
- Handle network interruptions and retry failed operations