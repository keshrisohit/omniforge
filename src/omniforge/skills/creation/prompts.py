"""LLM prompt templates for Skill Creation Assistant.

This module contains prompt templates for various LLM-based tasks in the
skill creation process, including pattern detection, question generation,
and skill metadata generation.
"""

# fmt: off
# ruff: noqa: E501
# Unified skill requirements analysis prompt
SKILL_REQUIREMENTS_ANALYSIS_PROMPT = """You are a skill requirements analyzer for an AI agent framework.
Analyze the user's skill description and conversation context to determine what the skill needs.

## USER'S SKILL DESCRIPTION:
{purpose}

## CONVERSATION CONTEXT:
{conversation_context}

## YOUR TASK:
Analyze what this skill actually needs to function, and provide intelligent suggestions.

### 1. CAPABILITY ANALYSIS
Determine which capabilities this skill requires (true/false for each):
- **needs_file_operations**: Does it need to read/write files?
- **needs_external_knowledge**: Does it need reference docs, lookup tables, or domain knowledge?
- **needs_script_execution**: Does it need to run scripts, commands, or tools?
- **needs_multi_step_workflow**: Does it involve multiple sequential steps?

### 2. QUESTIONS TO ASK
Based on what's missing from the context, what questions should we ask the user?
Generate 2-3 specific, contextual questions that would help create a better skill.

### 3. TOOL SUGGESTIONS
What tool permissions does this skill need? Be specific.
Examples: ["Read", "Write", "Bash(git:*)", "Bash(npm:*)", "Bash(docker:*)"]

### 4. ASSET SUGGESTIONS
What supporting files would help this skill? Each suggestion should include:
- name: Filename (e.g., "checklist.md", "config.yaml")
- purpose: Why this asset is needed
- type: Asset type (e.g., "checklist", "template", "config")

### 5. REFERENCE SUGGESTIONS
What reference documentation topics would be useful? Each suggestion should include:
- topic: Topic name (e.g., "brand-guidelines", "api-endpoints")
- purpose: What information should be in this reference

### 6. SCRIPT SUGGESTIONS
What scripts or automation would this skill benefit from? Each suggestion should include:
- name: Script name (e.g., "deploy.sh", "validate.py")
- purpose: What the script should do
- language: Programming language (e.g., "bash", "python")

## GUIDELINES:
- Be practical and specific - suggest what would actually help
- Don't over-engineer - simple skills don't need complex assets
- Tailor suggestions to the specific use case, not generic patterns
- If something isn't needed, return empty array
- Explain your reasoning clearly

## OUTPUT FORMAT:
Respond with ONLY a JSON object:
{{
  "capabilities": {{
    "needs_file_operations": true|false,
    "needs_external_knowledge": true|false,
    "needs_script_execution": true|false,
    "needs_multi_step_workflow": true|false
  }},
  "questions_to_ask": ["question 1?", "question 2?"],
  "suggested_tools": ["tool1", "tool2"],
  "suggested_assets": [
    {{"name": "file.md", "purpose": "why needed", "type": "asset type"}}
  ],
  "suggested_references": [
    {{"topic": "topic-name", "purpose": "what info to include"}}
  ],
  "suggested_scripts": [
    {{"name": "script.sh", "purpose": "what it does", "language": "bash"}}
  ],
  "confidence": 0.0-1.0,
  "reasoning": "explanation of capability analysis and suggestions"
}}

## EXAMPLES:

**Example 1 - Simple transformation:**
Purpose: "Format product abbreviations to full names"
{{
  "capabilities": {{
    "needs_file_operations": false,
    "needs_external_knowledge": true,
    "needs_script_execution": false,
    "needs_multi_step_workflow": false
  }},
  "questions_to_ask": [
    "Can you provide 2-3 examples like 'PA -> Pro Analytics'?",
    "When should this formatting be applied?"
  ],
  "suggested_tools": [],
  "suggested_assets": [],
  "suggested_references": [
    {{"topic": "product-abbreviations", "purpose": "Mapping of abbreviations to full product names"}}
  ],
  "suggested_scripts": [],
  "confidence": 0.9,
  "reasoning": "Simple lookup transformation needs reference data but no file ops or scripts"
}}

**Example 2 - Deployment workflow:**
Purpose: "Deploy application to production servers"
{{
  "capabilities": {{
    "needs_file_operations": true,
    "needs_external_knowledge": false,
    "needs_script_execution": true,
    "needs_multi_step_workflow": true
  }},
  "questions_to_ask": [
    "What are the deployment steps in order?",
    "What commands need to run?",
    "What should happen if deployment fails?"
  ],
  "suggested_tools": ["Read", "Bash(npm:*)", "Bash(pm2:*)"],
  "suggested_assets": [
    {{"name": "deploy-checklist.md", "purpose": "Track deployment progress through steps", "type": "checklist"}}
  ],
  "suggested_references": [],
  "suggested_scripts": [
    {{"name": "deploy.sh", "purpose": "Execute deployment commands", "language": "bash"}}
  ],
  "confidence": 0.85,
  "reasoning": "Multi-step automation needs scripts, file access, and workflow tracking"
}}

Now analyze the skill requirements:
"""

# Clarifying questions generation prompt
CLARIFYING_QUESTIONS_PROMPT = """You are an intelligent assistant helping create an AI agent skill.
Your role is to analyze the conversation history and generate smart, contextual clarifying questions.

## INSTRUCTIONS:
1. **Analyze the conversation flow** - Review what the user has already shared
2. **Ask follow-up questions** - Build on previous answers, don't repeat questions
3. **Focus on gaps** - Identify what critical information is still missing
4. **Be specific** - Ask targeted questions based on the user's domain/use case
5. **Avoid redundancy** - Don't ask about information already provided
6. **Be conversational** - Questions should feel natural, not robotic

## CONVERSATION HISTORY:
{conversation_history}

## CURRENT CONTEXT:
- Skill Purpose: {skill_purpose}
- Capabilities: {skill_capabilities}
- Examples provided: {has_examples}
- Triggers/contexts provided: {has_triggers}
- Workflow steps provided: {has_workflow_steps}

## WHAT TO ASK ABOUT (based on detected capabilities):
- **If no examples**: Ask for 2-3 concrete input/output examples
- **If no triggers**: Ask when/where this skill should be used
- **If unclear behavior**: Ask about edge cases, error handling, expected outputs
- **If needs_multi_step_workflow**: Ask about step-by-step process and decision points
- **If needs_external_knowledge**: Ask about knowledge sources and reference materials
- **If needs_script_execution**: Ask about commands, scripts, and failure handling

## GUIDELINES:
- Generate 2-3 questions maximum
- Questions should be specific to the user's context
- Use information from conversation history to ask smart follow-ups
- Avoid generic questions - tailor to the user's described use case
- If user mentioned specific examples/triggers, build on those rather than asking again

Respond with ONLY a JSON array of question strings:
["Question 1?", "Question 2?", "Question 3?"]

Example good questions (context-aware):
- "You mentioned formatting product names - could you give me 2-3 examples like 'PA' -> 'Pro Analytics'?"
- "When you're writing documentation, which specific sections or document types should trigger this skill?"
- "What should happen if the input doesn't match any known abbreviations?"
"""

# Skill name generation prompt
SKILL_NAME_GENERATION_PROMPT = """You are generating a skill name following Anthropic's Agent Skills guidelines.

Generate a kebab-case skill name that:
- Uses gerund form (ending in -ing) or descriptive nouns
- Is 1-64 characters maximum
- Contains only lowercase letters, numbers, and hyphens
- Starts with a lowercase letter
- Clearly describes the skill's purpose

Context:
- Purpose: {skill_purpose}
- Pattern: {skill_pattern}
- Examples: {examples}

Respond with ONLY a JSON object:
{{"name": "kebab-case-name", "alternatives": ["alt-1", "alt-2"]}}

Examples:
{{"name": "formatting-product-names", "alternatives": ["product-name-formatter", "name-formatting"]}}
{{"name": "data-validation", "alternatives": ["validating-data", "input-validator"]}}
"""

# Description generation prompt
DESCRIPTION_GENERATION_PROMPT = """You are generating a skill description following Anthropic's Agent Skills guidelines.

Generate a description that:
- Is written in third person
- Describes WHAT the skill does AND WHEN to use it
- Is 1-1024 characters maximum
- Is clear, concise, and actionable
- Avoids redundancy with the skill name

Context:
- Skill Name: {skill_name}
- Purpose: {skill_purpose}
- Pattern: {skill_pattern}
- Examples: {examples}
- Triggers: {triggers}

Respond with ONLY a JSON object:
{{"description": "Third person description of what the skill does and when to use it."}}

Example:
{{"description": "Formats product names into their full display form when writing documentation or customer-facing content. Use when abbreviations need to be expanded consistently."}}
"""

# SKILL.md body generation prompt following Anthropic's best practices
SKILL_BODY_GENERATION_PROMPT = """You are generating a SKILL.md file body following Anthropic's Agent Skills best practices.

## CRITICAL REQUIREMENTS FROM ANTHROPIC DOCUMENTATION:

### 1. CONCISENESS IS KEY
- Assume Claude is already very smart
- Only add context Claude doesn't already have
- Challenge each piece of information: "Does Claude really need this?"
- Keep body under 500 lines total
- Avoid over-explaining - Claude understands common concepts

### 2. STRUCTURE AND FORMAT
Start with a level-1 heading using the skill name, then include:
- Quick start section with immediate, actionable guidance
- Core instructions section with clear, step-by-step guidance
- Examples section with concrete input/output pairs
- Edge cases or special considerations (if relevant)

### 3. WRITING STYLE
- Use imperative form in instructions ("Use pdfplumber to extract", not "You should use")
- Be direct and actionable
- Provide concrete examples inline
- Avoid verbose explanations
- No time-sensitive information
- Use consistent terminology throughout
- **Use double quotes (not single quotes) for ALL string values in examples.**
  Apostrophes and contractions (I'd, can't, won't) break single-quoted strings.
  ✅ body: "Dear [Name], I'd like to discuss..."
  ❌ body: 'Dear [Name], I'd like to discuss...'  ← breaks YAML/Python parsers

### 4. PATH REFERENCES - CRITICAL FOR PORTABILITY

**ALWAYS use {{{{baseDir}}}} placeholder for skill-relative paths:**

✅ **CORRECT - Portable across environments:**
```
Read {{{{baseDir}}}}/config.json
python {{{{baseDir}}}}/scripts/analyzer.py --input data.json
Load template from {{{{baseDir}}}}/assets/template.html
```

❌ **INCORRECT - Will break when moved:**
```
Read /home/user/project/config.json
python /absolute/path/scripts/analyzer.py
Load template from C:\\Users\\project\\template.html
Read {{baseDir}}/config.json (Single curly braces are incorrect)
```

**Rules:**
- Use {{{{baseDir}}}} for ALL paths to scripts/, references/, assets/
- Never use absolute paths (starting with / or C:\\)
- Never hardcode user directories (/home/user/, /Users/name/)
- {{{{baseDir}}}} represents the skill's root directory
- Maintain portability across Linux, Mac, Windows

### 5. PROGRESSIVE DISCLOSURE - KEEPING IT CONCISE:

**IMPORTANT:** Only include essential, actionable context in `SKILL.md`.

- **Move to references/**: Detailed domain knowledge, large lookup tables, API schemas, complex configurations, background concepts.
- **Keep in SKILL.md**: Prompting strategy, direct instructions, core input/output examples, usage triggers, and clear step-by-step logic.
- **assume Claude is capable**: Don't over-explain basic Python or Bash usage unless specific flags or patterns are required.

### 6. TOOL UTILIZATION:

**IMPORTANT:** Reference allowed tools by name in your instructions.

- If the skill has "Read" permission, use "Use the `Read` tool to...".
- If it has "Bash" permission, specify exact commands to run via `Bash`.
- Always correlate instructions with the `allowed_tools` provided in the context.

### 7. CAPABILITY-BASED GUIDANCE:

**IMPORTANT:** Tailor the skill content based on actual capabilities needed, not rigid patterns.

**If needs basic transformation:**
- Focus on clear input/output transformations
- Provide 2-3 concrete examples inline
- Keep instructions direct and actionable
- Include edge cases if relevant

**If needs_multi_step_workflow:**
- Use numbered lists for sequential steps
- Provide a checklist that can be copied and tracked
- Include decision points if applicable
- Specify what happens at each step
- Note dependencies between steps

**If needs_external_knowledge:**
- Include "Read {{{{baseDir}}}}/references/[topic].md" instructions
- Organize by topic or domain
- Point to external documentation as needed
- Keep reference material concise

**If needs_script_execution:**
- Create the script based on it s description
- Specify input parameters and outputs
- Include error handling guidance
- Note any prerequisites or dependencies
- Show exact command syntax
- Always use {{{{baseDir}}}}/scripts/ for script paths
- Esnure that script can be executed from any directory

**If needs_file_operations:**
- Specify which files to read/write
- Show expected file formats
- Include path examples using {{{{baseDir}}}}
- Note any file validation requirements

### 6. EXAMPLE PATTERNS TO FOLLOW:

**Good Simple Skill Example:**
```markdown
# Product Name Formatter

## Quick start

Use this skill when writing documentation or customer-facing content.

## Core transformation

Transform input following these examples:
- Input: PA → Output: Pro Analytics
- Input: CS → Output: Customer Success
- Input: PM → Output: Product Management

## Instructions

1. Identify the abbreviation in the text
2. Look up the corresponding full form
3. Replace the abbreviation with the proper display name
4. Maintain proper capitalization and formatting

## Edge cases

- If abbreviation is unknown, keep original text
- Preserve surrounding punctuation and spacing
- Handle multiple abbreviations in same sentence
```

**Good Workflow Skill Example:**
```markdown
# Data Processing Workflow

## Workflow

Copy this checklist and track your progress:

```
Task Progress:
- [ ] Step 1: Validate input data
- [ ] Step 2: Transform and clean data
- [ ] Step 3: Generate output report
```

### Step 1: Validate input data

Check that all required fields are present and properly formatted.

### Step 2: Transform and clean data

Apply transformations and remove invalid entries.

### Step 3: Generate output report

Create final report with processed data.

## Validation

After completing all steps:
1. Verify all data is properly formatted
2. Check for any validation errors
3. Confirm output matches expected format
```

## YOUR TASK:

Generate the Markdown body content for this skill:

**Skill Information:**
- Name: {skill_name}
- Description: {skill_description}
- Purpose: {skill_purpose}
- Capabilities: {skill_capabilities}

**Examples provided:**
{examples}

**Triggers/Contexts:**
{triggers}

{workflow_section}{references_section}{scripts_section}

**IMPORTANT - Loading References:**
If reference topics are listed above, reference documentation files will be generated in the references/ directory.
When writing the skill body, include instructions like:
"For detailed information on [topic], read {{{{baseDir}}}}/references/[topic].md"

This follows progressive disclosure - keep the main SKILL.md concise and point to references for details.

## OUTPUT REQUIREMENTS:

1. DO NOT include YAML frontmatter (---) - generate ONLY the Markdown body
2. Start with # {skill_name} as the first line
3. Follow the pattern-specific template above
4. Be concise - under 500 lines total
5. Use concrete examples from the context provided
6. Make it immediately actionable for Claude
7. Assume Claude is smart - don't over-explain
8. Use imperative form in instructions
9. **Use double quotes for all string values in examples** (never single quotes).
   Single-quoted strings break if they contain apostrophes (I'd, can't, won't).
   ✅ Correct: body: "Dear [Name], I'd like to..."
   ❌ Wrong:   body: 'Dear [Name], I'd like to...'

Generate the Markdown body content now:
"""
# fmt: on

# Inference from context prompt
INFERENCE_FROM_CONTEXT_PROMPT = """You are an intelligent assistant analyzing a skill creation conversation.
Your role is to INFER missing information from the conversation context WITHOUT asking the user.

## CONVERSATION HISTORY:
{conversation_history}

## CURRENT CONTEXT:
- Skill Purpose: {skill_purpose}
- Pattern: {skill_pattern}
- Examples provided: {examples}
- Triggers provided: {triggers}
- Workflow steps: {workflow_steps}

## MISSING INFORMATION:
{missing_info}

## YOUR TASK:
Try to intelligently INFER the missing information based on:
1. The skill purpose and pattern
2. What the user has already shared
3. Common use cases for this type of skill
4. Reasonable defaults for this domain

## GUIDELINES:
- Make reasonable assumptions based on context
- Infer from the purpose what triggers/contexts would make sense
- Generate plausible examples if the pattern is clear
- Don't invent complex details - keep inferences simple and reasonable
- If truly cannot infer, mark as "CANNOT_INFER"

Respond with ONLY a JSON object:
{{
  "examples": ["inferred example 1", "inferred example 2"] or "CANNOT_INFER",
  "triggers": ["inferred trigger 1", "inferred trigger 2"] or "CANNOT_INFER",
  "workflow_steps": ["step 1", "step 2"] or "CANNOT_INFER",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of inferences"
}}

Example response:
{{
  "examples": ["Input: PA, Output: Pro Analytics", "Input: CS, Output: Customer Success"],
  "triggers": ["writing documentation", "creating customer-facing content"],
  "workflow_steps": "CANNOT_INFER",
  "confidence": 0.75,
  "reasoning": "Based on 'formatting product names' purpose, inferred common abbreviations and typical usage contexts"
}}
"""

# Should ask clarification decision prompt
SHOULD_ASK_CLARIFICATION_PROMPT = """You are deciding whether to ask clarifying questions or proceed with skill creation.

## CURRENT CONTEXT:
- Skill Purpose: {skill_purpose}
- Pattern: {skill_pattern}
- Examples: {examples}
- Triggers: {triggers}
- Workflow steps: {workflow_steps}
- Inference attempted: {inference_attempted}
- Inference results: {inference_results}

## DECISION CRITERIA:
Ask clarification ONLY if:
1. Critical information is completely missing AND cannot be inferred
2. The skill purpose is too vague to understand
3. Examples are needed but the domain is too specialized to infer
4. Workflow steps are required but the process is unclear

DO NOT ask if:
1. Reasonable inferences can be made
2. We have enough context for a simple skill
3. The missing information is minor/optional
4. User has already provided sufficient detail

Respond with ONLY a JSON object:
{{
  "should_ask": true|false,
  "reasoning": "brief explanation",
  "confidence": 0.0-1.0
}}

Example:
{{
  "should_ask": false,
  "reasoning": "Have clear purpose, reasonable examples inferred, and typical triggers identified",
  "confidence": 0.8
}}
"""

# Requirements extraction prompt - LLM-based extraction of all skill information
REQUIREMENTS_EXTRACTION_PROMPT = """You are an intelligent requirements extractor for AI agent skill creation.
Your task is to analyze the user's message and extract structured skill requirements.

## CONVERSATION CONTEXT:
- Skill Purpose: {skill_purpose}
- Skill Patterns: {skill_patterns}
- Previous conversation: {conversation_history}

## USER'S MESSAGE:
{user_message}

## YOUR TASK:
Extract ALL relevant information from the user's message into structured fields:

### 1. EXAMPLES (input/output pairs or demonstrations)
Look for:
- Explicit format: "Input: X, Output: Y" or "X -> Y" or "X => Y"
- Bullet points with examples
- "For example", "like", "such as" followed by examples
- Direct demonstrations of the skill's behavior
- Test cases or sample data

Extract as: List of strings in format "Input: X, Output: Y" or descriptive examples

### 2. TRIGGERS/CONTEXTS (when to use the skill)
Look for:
- "when", "whenever", "while", "during", "if", "use when"
- Situational descriptions ("when writing docs", "during code review")
- Context indicators ("in presentations", "for customer-facing content")
- Conditional statements about usage

Extract as: List of contextual trigger descriptions

### 3. WORKFLOW STEPS (for multi-step processes)
Look for:
- Numbered lists (1., 2., 3.)
- Sequential indicators: "first", "then", "next", "after that", "finally"
- Process descriptions with multiple stages
- Step-by-step instructions

Extract as: List of step descriptions in order

### 4. REFERENCE TOPICS (for knowledge-based skills)
Look for:
- Mentions of "documentation", "guidelines", "reference", "manual", "handbook"
- Knowledge domains or topic areas
- Sources of information to consult
- Documentation references

Extract as: List of reference topic areas

### 5. SCRIPTS/COMMANDS (for automation skills)
Look for:
- Code blocks with triple backticks
- Command-line instructions starting with $ or >
- Shell commands, scripts, or automation instructions
- Technical commands or CLI operations

Extract as: List of script/command strings

## EXTRACTION GUIDELINES:
1. **Be comprehensive** - Extract ALL relevant information, don't miss details
2. **Be specific** - Preserve exact examples, commands, and technical details
3. **Normalize format** - Convert varied formats to consistent structures
4. **Don't invent** - Only extract what's explicitly stated or clearly implied
5. **Handle multiple items** - User may provide several examples, triggers, or steps
6. **Context-aware** - Use conversation history and skill pattern to guide extraction
7. **Empty is OK** - If user didn't provide information for a field, return empty array

## PATTERN-SPECIFIC FOCUS:
{pattern_specific_guidance}

## OUTPUT FORMAT:
Respond with ONLY a JSON object with these exact fields:
{{
  "examples": ["example 1", "example 2", ...] or [],
  "triggers": ["trigger 1", "trigger 2", ...] or [],
  "workflow_steps": ["step 1", "step 2", ...] or [],
  "references_topics": ["topic 1", "topic 2", ...] or [],
  "scripts_needed": ["script 1", "script 2", ...] or [],
  "extraction_notes": "Brief notes about what was extracted and any ambiguities"
}}

## EXAMPLES:

**Example 1 - Simple pattern:**
User message: "Convert product codes to full names. For example: PA -> Pro Analytics, CS -> Customer Success. Use this when writing customer-facing documentation."

Response:
{{
  "examples": ["Input: PA, Output: Pro Analytics", "Input: CS, Output: Customer Success"],
  "triggers": ["writing customer-facing documentation"],
  "workflow_steps": [],
  "references_topics": [],
  "scripts_needed": [],
  "extraction_notes": "Extracted 2 input/output examples and 1 usage trigger"
}}

**Example 2 - Workflow pattern:**
User message: "Process data in 3 steps: 1. Validate the input format, 2. Transform using the mapping rules, 3. Generate the output report. Run this whenever new data files arrive."

Response:
{{
  "examples": [],
  "triggers": ["new data files arrive"],
  "workflow_steps": ["Validate the input format", "Transform using the mapping rules", "Generate the output report"],
  "references_topics": [],
  "scripts_needed": [],
  "extraction_notes": "Extracted 3-step workflow and 1 trigger condition"
}}

**Example 3 - Script pattern:**
User message: "Deploy using these commands: ```npm run build``` and then ```pm2 restart app```. Use when deploying to production."

Response:
{{
  "examples": [],
  "triggers": ["deploying to production"],
  "workflow_steps": [],
  "references_topics": [],
  "scripts_needed": ["npm run build", "pm2 restart app"],
  "extraction_notes": "Extracted 2 deployment scripts and 1 usage trigger"
}}

Now extract requirements from the user's message above:
"""

# Script generation and validation prompt
SCRIPT_GENERATION_PROMPT = """Generate production-ready scripts for the '{skill_name}' skill.

**Skill Purpose:** {skill_purpose}
**Description:** {skill_description}
**Capabilities:** {capabilities_desc}

**Required Scripts/Commands:**
{scripts_list}

**Language Requirements:** {language_note}

## GENERATION REQUIREMENTS:

### 1. CODE QUALITY
- Write clean, well-documented code
- Include comprehensive docstrings/comments
- Use meaningful variable and function names
- Follow language best practices (PEP 8 for Python, ShellCheck for Bash)

### 2. ERROR HANDLING
- Validate all inputs
- Handle errors gracefully with clear messages
- Use appropriate exit codes (0 for success, non-zero for errors)
- Include try-catch blocks (Python) or error traps (Bash)

### 3. SECURITY
- Never hardcode credentials, API keys, or secrets
- Use environment variables for sensitive data
- Validate and sanitize all inputs
- Avoid dangerous commands (rm -rf without safeguards, eval, etc.)
- Use {{baseDir}} for all paths to skill resources

### 4. PORTABILITY
- Use {{{{baseDir}}}} placeholder for all paths to scripts/, references/, assets/
- Make scripts executable from any directory
- Handle cross-platform differences where applicable
- Include shebang lines (#!/usr/bin/env python3, #!/bin/bash)

### 5. DOCUMENTATION
- Add header comments explaining script purpose
- Document all parameters and return values
- Include usage examples in comments or README
- Specify dependencies and prerequisites

### 6. VALIDATION
- Scripts must be syntactically correct
- Include basic self-tests or validation logic
- Log important operations
- Provide helpful error messages

## FILE STRUCTURE:

Generate the following files as needed:

- **scripts/*.py or *.sh** - Implementation scripts
- **scripts/README.md** - Usage documentation
- **requirements.txt** (Python) or **scripts/dependencies.txt** (Bash) - Dependencies

## OUTPUT FORMAT:

For EACH file, use this exact format:
```
FILE: scripts/filename.ext
CONTENT:
<file content here>
END_FILE
```

## EXAMPLE SCRIPT STRUCTURE (Python):

```python
#!/usr/bin/env python3
\"\"\"
Script purpose and description.

Usage:
    python {{{{baseDir}}}}/scripts/example.py --input data.json

Requirements:
    - Python 3.9+
    - Required packages listed in requirements.txt
\"\"\"

import argparse
import json
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    \"\"\"Main entry point.\"\"\"
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--input", required=True, help="Input file path")

    try:
        args = parser.parse_args()

        # Validate input
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {{input_path}}")
            sys.exit(1)

        # Process
        logger.info("Processing...")
        # Implementation here

        logger.info("Completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## EXAMPLE SCRIPT STRUCTURE (Bash):

```bash
#!/bin/bash
#
# Script purpose and description.
#
# Usage:
#     bash {{{{baseDir}}}}/scripts/example.sh --input data.txt
#
# Requirements:
#     - bash 4.0+
#     - jq (for JSON processing)

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
NC='\\033[0m' # No Color

# Logging functions
log_info() {{ echo -e "${{GREEN}}INFO:${{NC}} $1"; }}
log_error() {{ echo -e "${{RED}}ERROR:${{NC}} $1" >&2; }}

# Main function
main() {{
    local input_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --input)
                input_file="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate input
    if [[ -z "$input_file" ]]; then
        log_error "Input file required"
        exit 1
    fi

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        exit 1
    fi

    # Process
    log_info "Processing..."
    # Implementation here

    log_info "Completed successfully"
    exit 0
}}

# Run main function
main "$@"
```

Generate complete, production-ready scripts now:
"""

# Script validation prompt
SCRIPT_VALIDATION_PROMPT = """Validate the following script for production readiness.

**Script Path:** {script_path}
**Language:** {language}

**Script Content:**
```{language}
{script_content}
```

## VALIDATION CHECKS:

### 1. SYNTAX
- Check for syntax errors
- Verify proper language constructs
- Ensure valid shebang line

### 2. SECURITY
- No hardcoded credentials or API keys
- No dangerous commands without safeguards (rm -rf, eval, exec)
- Input validation present
- No use of absolute paths (should use {{{{baseDir}}}})

### 3. ERROR HANDLING
- Proper error handling (try-catch, set -e, etc.)
- Clear error messages
- Appropriate exit codes

### 4. CODE QUALITY
- Meaningful variable/function names
- Sufficient comments/documentation
- Follows best practices
- Header documentation present

### 5. PORTABILITY
- Uses {{{{baseDir}}}} for skill resource paths
- Can be executed from any directory
- Cross-platform considerations (if applicable)

## OUTPUT FORMAT:

Respond with ONLY a JSON object:
{{{{
  "is_valid": true|false,
  "syntax_errors": ["error 1", "error 2"] or [],
  "security_issues": ["issue 1", "issue 2"] or [],
  "quality_issues": ["issue 1", "issue 2"] or [],
  "warnings": ["warning 1", "warning 2"] or [],
  "suggestions": ["suggestion 1", "suggestion 2"] or [],
  "overall_assessment": "Brief assessment of script quality and readiness"
}}}}

Validate the script now:
"""
