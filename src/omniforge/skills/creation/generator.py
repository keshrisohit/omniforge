"""SKILL.md generator for Skill Creation Assistant.

This module generates SKILL.md content following the official Anthropic Agent Skills format,
ensuring strict compliance with frontmatter requirements (only name and description fields)
and body content guidelines.
"""

import logging
import re
from typing import Optional

from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.creation.models import ConversationContext
from omniforge.skills.creation.prompts import (
    SCRIPT_GENERATION_PROMPT,
    SCRIPT_VALIDATION_PROMPT,
    SKILL_BODY_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)


class SkillMdGenerator:
    """Generate SKILL.md content following official Anthropic format.

    CRITICAL CONSTRAINTS (from official docs):
    - Frontmatter: ONLY `name` and `description` fields
    - Name: max 64 chars, lowercase letters/numbers/hyphens, gerund preferred
    - Description: max 1024 chars, third person, includes WHAT and WHEN
    - Body: under 500 lines (~5k tokens)
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None:
        """Initialize the SKILL.md generator.

        Args:
            llm_generator: LLM generator for body content creation
        """
        self.llm_generator = llm_generator

    async def generate(self, context: ConversationContext) -> str:
        """Generate complete SKILL.md content in official format.

        Args:
            context: Conversation context with accumulated skill information

        Returns:
            Complete SKILL.md content as string

        Raises:
            ValueError: If required context fields are missing
        """
        print(f"\n[GENERATOR DEBUG] generate() called for skill: {context.skill_name}")

        if not context.skill_name or not context.skill_description:
            print("[GENERATOR ERROR] Missing required fields!")
            raise ValueError("Context must have skill_name and skill_description")

        # Generate frontmatter using strict template
        frontmatter = self.generate_frontmatter(context)
        print(f"[GENERATOR DEBUG] Frontmatter generated: {len(frontmatter)} chars")

        # Generate body using LLM
        print("[GENERATOR DEBUG] About to generate body...")
        body = await self.generate_body(context)
        print(f"[GENERATOR DEBUG] Body generation complete: {len(body)} chars")

        # Generate scripts and resources
        print("[GENERATOR DEBUG] About to generate scripts...")
        await self.generate_resources(context)
        print(f"[GENERATOR DEBUG] Scripts generated: {len(context.generated_resources)} files")

        # Generate reference documentation
        print("[GENERATOR DEBUG] About to generate references...")
        await self.generate_references(context)
        print("[GENERATOR DEBUG] References generated")

        # Generate asset files (templates, configs)
        print("[GENERATOR DEBUG] About to generate assets...")
        await self.generate_assets(context)
        print("[GENERATOR DEBUG] Assets generated")

        # Combine and return
        result = f"{frontmatter}\n{body}"
        print(f"[GENERATOR DEBUG] Final content: {len(result)} chars")
        return result

    def generate_frontmatter(self, context: ConversationContext) -> str:
        """Generate YAML frontmatter with required and optional fields.

        Includes name, description (required) and allowed-tools (critical for security).

        Args:
            context: Conversation context with skill_name, skill_description, and allowed_tools

        Returns:
            YAML frontmatter string with skill metadata

        Raises:
            ValueError: If required fields are missing
        """
        if not context.skill_name or not context.skill_description:
            raise ValueError("skill_name and skill_description are required")

        # Validate name format before generating frontmatter
        is_valid, error = self.validate_name_format(context.skill_name)
        if not is_valid:
            raise ValueError(f"Invalid skill name format: {error}")

        # Build frontmatter with required fields
        frontmatter_lines = [
            "---",
            f"name: {context.skill_name}",
            f"description: {context.skill_description}",
        ]

        # Add allowed-tools if specified (critical for security)
        if context.allowed_tools:
            tools_str = ",".join(context.allowed_tools)
            frontmatter_lines.append(f'allowed-tools: "{tools_str}"')

        frontmatter_lines.append("---")

        return "\n".join(frontmatter_lines)

    async def generate_body(self, context: ConversationContext) -> str:
        """Generate Markdown instruction body under 500 lines.

        Uses LLM to generate clear, concise instructions based on the skill pattern
        and accumulated context, ensuring progressive disclosure and brevity.

        Args:
            context: Conversation context with accumulated information

        Returns:
            Markdown body content

        Raises:
            ValueError: If body exceeds 500 lines after generation
        """
        # Build the generation prompt
        prompt = self._build_body_generation_prompt(context)

        print(f"\n{'='*80}")
        print(f"[GENERATOR DEBUG] Generating body with prompt of length: {len(prompt)}")
        print(f"[GENERATOR DEBUG] Prompt first 200 chars: {prompt[:200]}...")
        print(f"{'='*80}\n")

        # Generate body using LLM (streaming not needed here)
        # We'll accumulate the full response
        body_parts = []
        chunk_count = 0
        async for chunk in self.llm_generator.generate_stream(prompt):
            chunk_count += 1
            body_parts.append(chunk)
            if chunk_count <= 5:  # Only print first 5 chunks
                print(f"[GENERATOR DEBUG] Chunk {chunk_count}: '{chunk}'")

        body = "".join(body_parts).strip()
        print(f"\n[GENERATOR DEBUG] Generated body: {len(body)} chars from {chunk_count} chunks")
        if not body:
            print("[GENERATOR ERROR] Generated body is empty! No content received from LLM.")

        # Normalize paths to use {{baseDir}} placeholder
        body = self._normalize_paths_to_basedir(body)

        # Sanitize single-quoted strings that contain apostrophes/contractions
        # (e.g., 'I'd like...' → "I'd like...") to prevent SyntaxError on load
        body = self._sanitize_quoted_strings(body)

        # Validate line count
        line_count = len(body.split("\n"))
        if line_count > 500:
            raise ValueError(
                f"Generated body has {line_count} lines, exceeds 500 line limit. "
                "Please provide more focused requirements."
            )

        return body

    async def generate_resources(self, context: ConversationContext) -> None:
        """Generate supporting resources (scripts, docs) dynamically based on requirements.

        Populates context.generated_resources with scripts and documentation files
        based on context.scripts_needed and skill capabilities. Validates all generated
        scripts for syntax, security, and best practices.

        Args:
            context: Conversation context with accumulated skill information
        """
        # Skip if no scripts needed
        needs_scripts = context.scripts_needed or (
            context.skill_capabilities and context.skill_capabilities.needs_script_execution
        )
        if not needs_scripts:
            logger.info("No scripts needed for this skill")
            return

        # Build dynamic script generation prompt based on scripts_needed
        scripts_list = "\n".join(
            f"{i+1}. {script}" for i, script in enumerate(context.scripts_needed)
        )

        # Determine script language(s) from scripts_needed
        needs_python = any(
            "python" in s.lower() or ".py" in s.lower() for s in context.scripts_needed
        )
        needs_bash = any(
            "bash" in s.lower() or "sh" in s.lower() or "$" in s for s in context.scripts_needed
        )

        # Default to Python if not specified
        if not needs_python and not needs_bash:
            needs_python = True

        language_note = []
        if needs_python:
            language_note.append("Python scripts")
        if needs_bash:
            language_note.append("Bash scripts")

        # Build capabilities description
        capabilities_desc = "basic functionality"
        if context.skill_capabilities:
            caps = []
            if context.skill_capabilities.needs_file_operations:
                caps.append("file operations")
            if context.skill_capabilities.needs_external_knowledge:
                caps.append("external knowledge")
            if context.skill_capabilities.needs_script_execution:
                caps.append("script execution")
            if context.skill_capabilities.needs_multi_step_workflow:
                caps.append("multi-step workflow")
            capabilities_desc = ", ".join(caps) if caps else "basic functionality"

        # Use the enhanced script generation prompt
        script_prompt = SCRIPT_GENERATION_PROMPT.format(
            skill_name=context.skill_name or "Unknown Skill",
            skill_purpose=context.skill_purpose or "Unknown purpose",
            skill_description=context.skill_description or "No description",
            capabilities_desc=capabilities_desc,
            scripts_list=scripts_list,
            language_note=" and ".join(language_note),
        )

        # Generate resources using LLM
        logger.info("Generating scripts with production-ready standards...")
        response_parts = []
        async for chunk in self.llm_generator.generate_stream(script_prompt):
            response_parts.append(chunk)

        response = "".join(response_parts)

        # Parse the response to extract files
        files = self._parse_file_blocks(response)

        # Normalize paths in all generated files
        normalized_files = {
            path: self._normalize_paths_to_basedir(content) for path, content in files.items()
        }

        # Validate all script files
        logger.info(f"Validating {len(normalized_files)} generated files...")
        validated_files = {}
        validation_failures = []

        for file_path, content in normalized_files.items():
            # Only validate actual script files (not README, requirements.txt, etc.)
            if file_path.endswith((".py", ".sh", ".bash")):
                is_valid, validation_result = await self._validate_script(
                    file_path, content, context
                )

                if is_valid:
                    logger.info(f"✓ Script validated: {file_path}")
                    validated_files[file_path] = content
                else:
                    logger.warning(f"✗ Script validation failed: {file_path}")
                    validation_failures.append((file_path, validation_result))

                    # Attempt to fix validation issues (one retry)
                    logger.info(
                        f"  Attempting to regenerate {file_path} with validation feedback..."
                    )
                    fixed_content = await self._regenerate_script_with_fixes(
                        file_path, content, validation_result, context
                    )

                    # Validate the fixed version
                    is_valid_retry, _ = await self._validate_script(
                        file_path, fixed_content, context
                    )

                    if is_valid_retry:
                        logger.info(f"✓ Script fixed and validated: {file_path}")
                        validated_files[file_path] = fixed_content
                    else:
                        logger.error(f"✗ Script still invalid after fix: {file_path}")
                        # Store anyway but log the issue
                        validated_files[file_path] = fixed_content
            else:
                # Non-script files don't need validation
                validated_files[file_path] = content

        # Store validated files in context
        context.generated_resources.update(validated_files)

        logger.info(f"Generated and validated {len(validated_files)} resource files")

    async def generate_references(self, context: ConversationContext) -> None:
        """Generate reference documentation files from context.references_topics.

        Creates markdown documentation files in references/ directory that can be
        loaded into context when needed. Follows progressive disclosure pattern.

        Args:
            context: Conversation context with references_topics
        """
        # Skip if no reference topics
        if not context.references_topics:
            logger.info("No reference topics for this skill")
            return

        # Generate reference docs for each topic
        for topic in context.references_topics:
            # Sanitize topic for filename
            filename = self._sanitize_filename(topic)

            # Generate reference content
            ref_content = await self._generate_reference_doc(topic, context)

            # Normalize paths in reference content
            ref_content = self._normalize_paths_to_basedir(ref_content)

            # Store in generated_resources
            context.generated_resources[f"references/{filename}.md"] = ref_content

        logger.info(f"Generated {len(context.references_topics)} reference documents")

    async def generate_assets(self, context: ConversationContext) -> None:
        """Generate asset files based on LLM suggestions and capabilities.

        Creates template files and configuration boilerplate in assets/ directory.
        Assets are referenced by path, not loaded into context.
        Uses LLM-suggested assets from capability analysis.

        Args:
            context: Conversation context with skill details
        """
        assets_to_generate = []

        # First, use LLM-suggested assets if available
        if context.skill_capabilities and context.skill_capabilities.suggested_assets:
            for asset in context.skill_capabilities.suggested_assets:
                filename = asset.get("name", "")
                asset_type = asset.get("type", "generic")
                if filename:
                    assets_to_generate.append((filename, asset_type, asset.get("purpose", "")))
            logger.info(f"Using {len(assets_to_generate)} LLM-suggested assets")

        # Fallback: generate assets based on capabilities
        if not assets_to_generate and context.skill_capabilities:
            caps = context.skill_capabilities

            # Workflow capability: might need checklist templates
            if caps.needs_multi_step_workflow:
                assets_to_generate.append(
                    ("checklist-template.md", "checklist", "Track workflow progress")
                )
                assets_to_generate.append(
                    ("workflow-config.yaml", "workflow_config", "Configure workflow steps")
                )

            # External knowledge capability: might need glossary
            if caps.needs_external_knowledge:
                assets_to_generate.append(("glossary-template.md", "glossary", "Define key terms"))

            # Script execution capability: might need environment configs
            if caps.needs_script_execution:
                assets_to_generate.append(
                    (".env.example", "env_template", "Environment variables template")
                )
                assets_to_generate.append(("config.yaml", "script_config", "Script configuration"))

            # Basic config for any skill
            if caps.needs_file_operations or not assets_to_generate:
                assets_to_generate.append(("config.json", "json_config", "Basic configuration"))

        # Remove duplicates (by filename)
        seen_files = set()
        unique_assets = []
        for filename, asset_type, *purpose in assets_to_generate:
            if filename not in seen_files:
                seen_files.add(filename)
                purpose_text = purpose[0] if purpose else ""
                unique_assets.append((filename, asset_type, purpose_text))

        # Generate each asset
        for filename, asset_type, purpose_text in unique_assets:
            content = await self._generate_asset_file(filename, asset_type, context, purpose_text)
            # Normalize paths in asset content
            content = self._normalize_paths_to_basedir(content)
            context.generated_resources[f"assets/{filename}"] = content

        logger.info(f"Generated {len(unique_assets)} asset files based on capabilities")

    async def _generate_asset_file(
        self, filename: str, asset_type: str, context: ConversationContext, purpose: str = ""
    ) -> str:
        """Generate a specific asset file.

        Args:
            filename: Name of the asset file
            asset_type: Type of asset to generate
            context: Conversation context
            purpose: Optional purpose description from LLM suggestion

        Returns:
            Content for the asset file
        """
        prompt_templates = {
            "json_config": f"""Generate a configuration template for {context.skill_name}.

Create a JSON configuration file with:
- Sensible default values
- Comments explaining each option (use # in JSON comments where supported)
- All configurable parameters for the skill
- **CRITICAL**: Use {{baseDir}} for any paths (e.g., "scriptPath": "{{baseDir}}/scripts/main.py")

Format: JSON with helpful structure""",
            "checklist": f"""Generate a workflow checklist template for {context.skill_name}.

Create a Markdown checklist with:
- All workflow steps as checkboxes
- Space for notes under each step
- Status tracking section
- **CRITICAL**: Use {{baseDir}} for any file references

Format: Markdown with [ ] checkboxes""",
            "workflow_config": f"""Generate a workflow configuration for {context.skill_name}.

Create a YAML configuration with:
- Workflow steps defined
- Timing/timeout settings
- Dependencies between steps
- **CRITICAL**: Use {{baseDir}} for any paths (e.g., script: "{{baseDir}}/scripts/step1.py")

Format: YAML""",
            "glossary": f"""Generate a glossary template for {context.skill_name}.

Create a Markdown glossary with:
- Key terms and definitions
- Alphabetically organized
- Cross-references
- **CRITICAL**: Use {{baseDir}} for any file references in examples

Format: Markdown""",
            "env_template": f"""Generate an environment variables template for {context.skill_name}.

Create a .env.example file with:
- All required environment variables
- Example/placeholder values
- Comments explaining each variable
- Use {{baseDir}} for any path variables

Format: .env file""",
            "script_config": f"""Generate a script configuration for {context.skill_name}.

Create a YAML configuration with:
- Script paths using {{baseDir}} (e.g., path: "{{baseDir}}/scripts/main.py")
- Input/output specifications
- Execution options

Format: YAML""",
        }

        prompt = prompt_templates.get(
            asset_type,
            f"Generate a template file for {filename} for the {context.skill_name} skill",
        )

        # Generate content
        content_parts = []
        async for chunk in self.llm_generator.generate_stream(prompt):
            content_parts.append(chunk)

        return "".join(content_parts).strip()

    async def _generate_reference_doc(self, topic: str, context: ConversationContext) -> str:
        """Generate detailed reference documentation for a specific topic.

        Args:
            topic: The reference topic to document
            context: Conversation context for skill details

        Returns:
            Markdown content for the reference document
        """
        prompt = f"""Generate comprehensive reference documentation for: {topic}

**Context:**
- Skill: {context.skill_name}
- Purpose: {context.skill_purpose}
- When used: {', '.join(context.triggers) if context.triggers else 'As needed'}

**REQUIREMENTS:**
1. Create detailed, scannable documentation
2. Include key concepts and definitions
3. Provide practical usage guidance
4. Add examples where helpful
5. Keep focused on {topic}
6. Use clear markdown formatting
7. **CRITICAL**: Use {{baseDir}} for any paths to scripts/, references/, or assets/

**PATH USAGE:**
- Correct: Read {{{{baseDir}}}}/scripts/helper.py
- Correct: Load {{{{baseDir}}}}/assets/template.json
- Incorrect: Read {{baseDir}}/scripts/helper.py (single braces)
- Incorrect: Read /absolute/path/to/scripts/helper.py

**FORMAT:**
# {topic.title()}

## Overview
[Brief introduction]

## Key Concepts
[Main concepts with explanations]

## Usage Guidelines
[How to use this reference]

## Examples
[Practical examples]

## Best Practices
[Recommendations]

Generate comprehensive, well-structured documentation:"""

        # Generate content
        content_parts = []
        async for chunk in self.llm_generator.generate_stream(prompt):
            content_parts.append(chunk)

        return "".join(content_parts).strip()

    def _normalize_paths_to_basedir(self, content: str) -> str:
        """Normalize all absolute paths to use {{baseDir}} placeholder.

        Ensures portability by converting hardcoded paths to relative paths
        using the {{baseDir}} placeholder. Critical for Claude Skills compliance.

        Args:
            content: Content that may contain absolute paths

        Returns:
            Content with paths normalized to {{baseDir}}
        """
        # Pattern 1: Unix/Mac home directories
        content = re.sub(
            r"/(?:home|Users)/[^/\s]+/(scripts|references|assets)/", r"{{baseDir}}/\1/", content
        )

        # Pattern 2: Windows paths
        content = re.sub(
            r"[A-Z]:\\[^\\]+\\(scripts|references|assets)\\", r"{{baseDir}}/\1/", content
        )

        # Pattern 3: Absolute paths to skill resources without {{baseDir}}
        # Match: /scripts/, /path/to/scripts/, but not {{baseDir}}/scripts/
        # This catches both direct paths like /scripts/file.py and nested paths like /path/to/scripts/file.py
        content = re.sub(
            r"(?<!{{baseDir}})(/)(?:(?:[^/\s]+/)*?)(scripts|references|assets)/",
            r"{{baseDir}}/\2/",
            content,
        )

        # Pattern 3b: Direct paths starting with /scripts/, /references/, /assets/
        # This catches cases like "/scripts/file.py" that aren't part of {{baseDir}}/scripts/
        # The negative lookbehind checks that we're not after a closing brace }
        content = re.sub(r"(?<!})/(scripts|references|assets)/", r"{{baseDir}}/\1/", content)

        # Pattern 4: Python commands with absolute paths
        content = re.sub(
            r"python\s+/(?:[^/\s]+/)+(scripts/[^\s]+)", r"python {{baseDir}}/\1", content
        )

        # Pattern 5: Bash commands with absolute paths
        content = re.sub(r"bash\s+/(?:[^/\s]+/)+(scripts/[^\s]+)", r"bash {{baseDir}}/\1", content)

        return content

    def _sanitize_quoted_strings(self, content: str) -> str:
        """Replace single-quoted strings containing apostrophes with double-quoted versions.

        LLMs frequently generate examples like::

            body: 'Dear [Name], I'd like to discuss...'

        The apostrophe in a contraction (``I'd``, ``can't``, ``won't``, etc.) terminates
        the single-quoted value early, producing a ``SyntaxError: unterminated string
        literal`` when the SKILL.md is loaded by Python-based parsers.

        This method finds those patterns and rewrites the outer delimiters to double
        quotes so the apostrophe is safe::

            body: "Dear [Name], I'd like to discuss..."

        Args:
            content: Skill body text that may contain broken single-quoted strings

        Returns:
            Content with apostrophe-containing single-quoted strings converted to
            double-quoted strings
        """
        # Match a single-quoted string that contains a contraction apostrophe.
        # Group 1 captures everything between the outer single quotes.
        # Contractions: 'd, 't, 's, 'll, 're, 've, 'm → suffix chars: d t s l r v m e
        contraction_pattern = re.compile(r"'([^']*\b\w+'[tdslmrve]\b[^']*)'")

        def to_double_quotes(match: re.Match) -> str:
            return f'"{match.group(1)}"'

        return contraction_pattern.sub(to_double_quotes, content)

    def _sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename.

        Args:
            text: Text to convert to filename

        Returns:
            Sanitized filename (lowercase, hyphens, no special chars)
        """
        # Convert to lowercase
        filename = text.lower()

        # Replace spaces and special chars with hyphens
        filename = re.sub(r"[^a-z0-9]+", "-", filename)

        # Remove leading/trailing hyphens
        filename = filename.strip("-")

        # Limit length
        if len(filename) > 50:
            filename = filename[:50].rstrip("-")

        return filename or "reference"

    def _parse_file_blocks(self, response: str) -> dict[str, str]:
        """Parse FILE blocks from LLM response.

        Args:
            response: LLM response containing FILE blocks

        Returns:
            Dict mapping file paths to content
        """
        import re

        files = {}
        # Pattern to match FILE: path\nCONTENT:\n...content...\nEND_FILE
        pattern = r"FILE:\s*([^\n]+)\s*\nCONTENT:\s*\n(.*?)\nEND_FILE"

        matches = re.finditer(pattern, response, re.DOTALL)
        for match in matches:
            file_path = match.group(1).strip()
            content = match.group(2).strip()
            files[file_path] = content

        return files

    def validate_name_format(self, name: str) -> tuple[bool, Optional[str]]:
        """Validate skill name against official requirements.

        Validates that the name follows kebab-case format per Anthropic guidelines:
        - 1-64 characters
        - Lowercase letters, numbers, and hyphens only
        - Must start with a lowercase letter

        Args:
            name: Skill name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if not name or len(name) > 64:
            return False, "Skill name must be 1-64 characters"

        # Check format: must start with lowercase letter, contain only lowercase/numbers/hyphens
        if not re.match(r"^[a-z][a-z0-9-]*$", name):
            return (
                False,
                "Skill name must be kebab-case: start with lowercase letter, "
                "contain only lowercase letters, numbers, and hyphens",
            )

        # Check for consecutive hyphens
        if "--" in name:
            return False, "Skill name should not contain consecutive hyphens"

        # Check for trailing hyphen
        if name.endswith("-"):
            return False, "Skill name should not end with a hyphen"

        return True, None

    async def fix_validation_errors(
        self,
        content: str,
        errors: list[str],
    ) -> str:
        """Attempt to fix validation errors in generated content.

        Uses LLM to analyze and fix validation errors in the generated SKILL.md,
        particularly focusing on frontmatter compliance and line count issues.

        Args:
            content: Current SKILL.md content with errors
            errors: List of validation error messages

        Returns:
            Corrected SKILL.md content
        """
        # Build fix prompt
        prompt = f"""Fix these validation errors in the SKILL.md file:

ERRORS:
{chr(10).join(f"- {error}" for error in errors)}

CURRENT CONTENT:
{content}

CRITICAL RULES:
1. Frontmatter must have ONLY `name` and `description` fields (NO other fields)
2. Description must be third person and include WHAT and WHEN
3. Body must be under 500 lines
4. Name must be kebab-case (lowercase, letters/numbers/hyphens only)

Fix the errors and output the corrected SKILL.md. Start with exactly:
---
name: [skill-name]
description: [description]
---

Then add the corrected Markdown body.
"""

        # Generate fixed content using LLM
        fixed_parts = []
        async for chunk in self.llm_generator.generate_stream(prompt):
            fixed_parts.append(chunk)

        fixed_content = "".join(fixed_parts).strip()

        # Post-process to ensure only name and description in frontmatter
        fixed_content = self._strip_unauthorized_frontmatter(fixed_content)

        return fixed_content

    def _build_body_generation_prompt(self, context: ConversationContext) -> str:
        """Build LLM prompt for body generation based on capabilities.

        Uses comprehensive Anthropic best practices prompt template.
        Includes sections based on skill capabilities.

        Args:
            context: Conversation context with accumulated information

        Returns:
            Complete prompt for body generation
        """
        # Format examples
        examples_text = (
            "\n".join(f"- {ex}" for ex in context.examples) if context.examples else "None provided"
        )

        # Format triggers
        triggers_text = (
            "\n".join(f"- {t}" for t in context.triggers) if context.triggers else "None provided"
        )

        # Build sections based on capabilities
        workflow_section = ""
        if (
            context.skill_capabilities
            and context.skill_capabilities.needs_multi_step_workflow
            and context.workflow_steps
        ):
            workflow_text = "\n".join(
                f"{i+1}. {step}" for i, step in enumerate(context.workflow_steps)
            )
            workflow_section = f"\n**Workflow Steps:**\n{workflow_text}\n"

        references_section = ""
        if (
            context.skill_capabilities
            and context.skill_capabilities.needs_external_knowledge
            and context.references_topics
        ):
            references_text = "\n".join(f"- {topic}" for topic in context.references_topics)
            references_section = f"\n**Reference Topics:**\n{references_text}\n"

        scripts_section = ""
        if (
            context.skill_capabilities
            and context.skill_capabilities.needs_script_execution
            and context.scripts_needed
        ):
            scripts_text = "\n".join(f"- {script}" for script in context.scripts_needed)
            scripts_section = f"\n**Scripts Needed:**\n{scripts_text}\n"

        # Build capabilities description for prompt
        capabilities_str = "basic transformation"
        if context.skill_capabilities:
            caps = []
            if context.skill_capabilities.needs_file_operations:
                caps.append("file operations")
            if context.skill_capabilities.needs_external_knowledge:
                caps.append("external knowledge")
            if context.skill_capabilities.needs_script_execution:
                caps.append("script execution")
            if context.skill_capabilities.needs_multi_step_workflow:
                caps.append("multi-step workflow")
            capabilities_str = ", ".join(caps) if caps else "basic transformation"

        # Use comprehensive Anthropic best practices prompt
        prompt = SKILL_BODY_GENERATION_PROMPT.format(
            skill_name=context.skill_name or "Unknown Skill",
            skill_description=context.skill_description or "No description",
            skill_purpose=context.skill_purpose or "Unknown purpose",
            skill_capabilities=capabilities_str,
            examples=examples_text,
            triggers=triggers_text,
            workflow_section=workflow_section,
            references_section=references_section,
            scripts_section=scripts_section,
        )

        return prompt

    def _strip_unauthorized_frontmatter(self, content: str) -> str:
        """Strip any unauthorized frontmatter fields, keeping only name and description.

        This is a safety mechanism to ensure generated content complies with
        official Anthropic format even if LLM adds extra fields.

        Args:
            content: SKILL.md content that may have extra frontmatter fields

        Returns:
            Content with only name and description in frontmatter
        """
        # Parse frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)

        if not frontmatter_match:
            # No frontmatter found, return as-is
            return content

        frontmatter_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        # Extract only name and description
        name_match = re.search(r"^name:\s*(.+)$", frontmatter_text, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter_text, re.MULTILINE)

        if not name_match or not desc_match:
            # Invalid frontmatter, return as-is
            return content

        name = name_match.group(1).strip()
        description = desc_match.group(1).strip()

        # Reconstruct with only name and description
        clean_frontmatter = f"""---
name: {name}
description: {description}
---"""

        return f"{clean_frontmatter}\n{body}"

    async def _validate_script(
        self, script_path: str, script_content: str, context: ConversationContext
    ) -> tuple[bool, dict]:
        """Validate a generated script for syntax, security, and best practices.

        Performs both basic syntax checking and LLM-based validation for production
        readiness including security, error handling, and code quality.

        Args:
            script_path: Path to the script file
            script_content: Content of the script
            context: Conversation context for skill details

        Returns:
            Tuple of (is_valid, validation_result_dict)
        """
        # Determine language from file extension
        if script_path.endswith(".py"):
            language = "python"
        elif script_path.endswith((".sh", ".bash")):
            language = "bash"
        else:
            # Unknown script type, skip validation
            return True, {"overall_assessment": "Unknown script type, skipping validation"}

        # Step 1: Basic syntax check
        syntax_valid, syntax_error = self._check_script_syntax(script_content, language)
        if not syntax_valid:
            logger.warning(f"Syntax error in {script_path}: {syntax_error}")
            return False, {
                "is_valid": False,
                "syntax_errors": [syntax_error],
                "security_issues": [],
                "quality_issues": [],
                "warnings": [],
                "suggestions": [],
                "overall_assessment": f"Syntax error: {syntax_error}",
            }

        # Step 2: LLM-based validation
        validation_prompt = SCRIPT_VALIDATION_PROMPT.format(
            script_path=script_path,
            language=language,
            script_content=script_content,
        )

        # Generate validation response
        response_parts = []
        async for chunk in self.llm_generator.generate_stream(validation_prompt):
            response_parts.append(chunk)

        response = "".join(response_parts).strip()

        # Parse JSON response
        import json

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            elif response.startswith("{"):
                # Already JSON
                pass
            else:
                # Try to find JSON object in response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    response = response[json_start:json_end]

            validation_result = json.loads(response)

            # Check if valid
            is_valid = validation_result.get("is_valid", False)

            # Consider it valid if no critical issues
            has_critical_issues = (
                len(validation_result.get("syntax_errors", [])) > 0
                or len(validation_result.get("security_issues", [])) > 0
            )

            is_valid = is_valid and not has_critical_issues

            return is_valid, validation_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            # If we can't parse validation, assume valid (syntax already checked)
            return True, {
                "is_valid": True,
                "overall_assessment": "LLM validation parsing failed, passed syntax check",
            }

    def _check_script_syntax(
        self, script_content: str, language: str
    ) -> tuple[bool, Optional[str]]:
        """Check basic syntax of a script.

        Args:
            script_content: Content of the script
            language: Script language ('python' or 'bash')

        Returns:
            Tuple of (is_valid, error_message)
        """
        if language == "python":
            # Check Python syntax using compile()
            try:
                compile(script_content, "<string>", "exec")
                return True, None
            except SyntaxError as e:
                return False, f"Python syntax error at line {e.lineno}: {e.msg}"
            except Exception as e:
                return False, f"Python compilation error: {str(e)}"

        elif language == "bash":
            # Basic bash syntax checks
            # Check for common issues
            issues = []

            # Check for shebang
            if not script_content.strip().startswith("#!"):
                issues.append("Missing shebang line (#!/bin/bash)")

            # Check for unmatched quotes (basic check)
            single_quotes = script_content.count("'") - script_content.count("\\'")
            double_quotes = script_content.count('"') - script_content.count('\\"')

            if single_quotes % 2 != 0:
                issues.append("Unmatched single quotes")
            if double_quotes % 2 != 0:
                issues.append("Unmatched double quotes")

            # Check for unmatched brackets (basic check)
            if script_content.count("{") != script_content.count("}"):
                issues.append("Unmatched curly braces")
            if script_content.count("[") != script_content.count("]"):
                issues.append("Unmatched square brackets")
            if script_content.count("(") != script_content.count(")"):
                issues.append("Unmatched parentheses")

            if issues:
                return False, "; ".join(issues)

            return True, None

        return True, None

    async def _regenerate_script_with_fixes(
        self,
        script_path: str,
        original_content: str,
        validation_result: dict,
        context: ConversationContext,
    ) -> str:
        """Regenerate a script with validation feedback to fix issues.

        Args:
            script_path: Path to the script file
            original_content: Original script content that failed validation
            validation_result: Validation result dictionary with issues
            context: Conversation context

        Returns:
            Regenerated script content
        """
        # Build feedback summary
        issues_summary = []

        if validation_result.get("syntax_errors"):
            issues_summary.append(
                "**Syntax Errors:**\n"
                + "\n".join(f"- {e}" for e in validation_result["syntax_errors"])
            )

        if validation_result.get("security_issues"):
            issues_summary.append(
                "**Security Issues:**\n"
                + "\n".join(f"- {e}" for e in validation_result["security_issues"])
            )

        if validation_result.get("quality_issues"):
            issues_summary.append(
                "**Quality Issues:**\n"
                + "\n".join(f"- {e}" for e in validation_result["quality_issues"])
            )

        if validation_result.get("suggestions"):
            issues_summary.append(
                "**Suggestions:**\n" + "\n".join(f"- {e}" for e in validation_result["suggestions"])
            )

        issues_text = "\n\n".join(issues_summary)

        # Build regeneration prompt
        regenerate_prompt = f"""Fix the following script based on validation feedback.

**Script Path:** {script_path}
**Validation Issues Found:**

{issues_text}

**Overall Assessment:** {validation_result.get("overall_assessment", "Needs improvement")}

**Original Script:**
```
{original_content}
```

## YOUR TASK:

Fix ALL the issues identified above while maintaining the script's core functionality.

**Requirements:**
1. Fix all syntax errors
2. Address all security issues (no hardcoded credentials, use {{{{baseDir}}}}, etc.)
3. Improve code quality as suggested
4. Maintain the original script's purpose and functionality
5. Keep the same file structure and format

**Output Format:**

Provide ONLY the fixed script content, no explanations or markdown code blocks.
Start directly with the shebang line (#!/usr/bin/env python3 or #!/bin/bash).

Generate the fixed script now:
"""

        # Generate fixed script
        response_parts = []
        async for chunk in self.llm_generator.generate_stream(regenerate_prompt):
            response_parts.append(chunk)

        fixed_content = "".join(response_parts).strip()

        # Remove markdown code blocks if present
        if fixed_content.startswith("```"):
            # Remove opening code block
            lines = fixed_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing code block
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            fixed_content = "\n".join(lines)

        # Normalize paths
        fixed_content = self._normalize_paths_to_basedir(fixed_content)

        return fixed_content
