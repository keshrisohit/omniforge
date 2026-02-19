"""Requirements gatherer for Skill Creation Assistant.

This module implements the RequirementsGatherer class that intelligently collects
skill requirements through clarifying questions, pattern detection, and context
sufficiency checking.
"""

import json
import logging
import re
from typing import Any

from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.creation.models import ConversationContext, SkillCapabilities
from omniforge.skills.creation.prompts import (
    CLARIFYING_QUESTIONS_PROMPT,
    DESCRIPTION_GENERATION_PROMPT,
    INFERENCE_FROM_CONTEXT_PROMPT,
    REQUIREMENTS_EXTRACTION_PROMPT,
    SHOULD_ASK_CLARIFICATION_PROMPT,
    SKILL_NAME_GENERATION_PROMPT,
    SKILL_REQUIREMENTS_ANALYSIS_PROMPT,
)

logger = logging.getLogger(__name__)


class RequirementsGatherer:
    """Generate clarifying questions and extract skill requirements.

    This class intelligently collects skill requirements through:
    - Skill pattern detection (Simple, Workflow, Reference, Script)
    - Contextual clarifying question generation
    - User response parsing and requirement extraction
    - Context sufficiency checking

    Attributes:
        llm_generator: LLM generator for intelligent question generation
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None:
        """Initialize RequirementsGatherer with LLM generator.

        Args:
            llm_generator: LLM generator for generating questions and parsing responses
        """
        self.llm_generator = llm_generator

    async def analyze_skill_requirements(
        self, purpose: str, context: ConversationContext
    ) -> SkillCapabilities:
        """Analyze skill requirements and determine capabilities needed.

        Uses LLM to determine what capabilities the skill needs, suggest
        questions to ask, and recommend tools, assets, references, and scripts.

        Args:
            purpose: User's description of the skill purpose
            context: Current conversation context for additional context

        Returns:
            SkillCapabilities with capability flags and LLM suggestions

        Examples:
            >>> gatherer = RequirementsGatherer(llm_generator)
            >>> capabilities = await gatherer.analyze_skill_requirements(
            ...     "Deploy app using scripts",
            ...     context
            ... )
            >>> assert capabilities.needs_script_execution is True
        """
        try:
            # Format conversation context
            conversation_ctx = self._format_conversation_history(context.message_history)

            # Generate prompt
            prompt = SKILL_REQUIREMENTS_ANALYSIS_PROMPT.format(
                purpose=purpose,
                conversation_context=conversation_ctx
            )

            # Call LLM for analysis
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            response_json = json.loads(response_text)

            # Extract capabilities
            capabilities_data = response_json.get("capabilities", {})
            capabilities = SkillCapabilities(
                needs_file_operations=capabilities_data.get("needs_file_operations", False),
                needs_external_knowledge=capabilities_data.get("needs_external_knowledge", False),
                needs_script_execution=capabilities_data.get("needs_script_execution", False),
                needs_multi_step_workflow=capabilities_data.get("needs_multi_step_workflow", False),
                suggested_tools=response_json.get("suggested_tools", []),
                suggested_assets=response_json.get("suggested_assets", []),
                suggested_references=response_json.get("suggested_references", []),
                suggested_scripts=response_json.get("suggested_scripts", []),
                confidence=response_json.get("confidence", 0.0),
                reasoning=response_json.get("reasoning", "")
            )

            logger.info(
                f"Analyzed skill requirements - Capabilities: "
                f"file_ops={capabilities.needs_file_operations}, "
                f"knowledge={capabilities.needs_external_knowledge}, "
                f"scripts={capabilities.needs_script_execution}, "
                f"workflow={capabilities.needs_multi_step_workflow}, "
                f"confidence={capabilities.confidence:.2f}"
            )

            return capabilities

        except Exception as e:
            logger.warning(f"Failed to analyze skill requirements: {e}, using defaults")
            # Fallback to basic capabilities
            return SkillCapabilities(
                needs_file_operations=False,
                needs_external_knowledge=False,
                needs_script_execution=False,
                needs_multi_step_workflow=False,
                suggested_tools=[],
                suggested_assets=[],
                suggested_references=[],
                suggested_scripts=[],
                confidence=0.3,
                reasoning="Failed to analyze, using default capabilities"
            )

    async def generate_clarifying_questions(
        self,
        context: ConversationContext,
    ) -> list[str]:
        """Generate questions based on conversation history and missing context.

        Uses LLM with full conversation history to generate intelligent,
        context-aware clarifying questions. Falls back to pattern templates
        only if LLM fails.

        Args:
            context: Current conversation context with message history

        Returns:
            List of 2-3 clarifying questions

        Examples:
            >>> context = ConversationContext(
            ...     skill_purpose="Format product names",
            ...     skill_pattern=SkillPattern.SIMPLE,
            ...     message_history=[
            ...         {"role": "user", "content": "I need a skill to format names"},
            ...         {"role": "assistant", "content": "What kind of names?"}
            ...     ]
            ... )
            >>> questions = await gatherer.generate_clarifying_questions(context)
            >>> assert len(questions) >= 2
        """
        try:
            # Build context summary
            has_examples = len(context.examples) > 0
            has_triggers = len(context.triggers) > 0
            has_workflow_steps = len(context.workflow_steps) > 0

            # Format conversation history for the prompt
            conversation_history = self._format_conversation_history(context.message_history)

            # Format capabilities for prompt
            capabilities_str = "Not analyzed yet"
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

            # Use LLM to generate contextual questions based on full conversation
            prompt = CLARIFYING_QUESTIONS_PROMPT.format(
                conversation_history=conversation_history,
                skill_purpose=context.skill_purpose or "Not specified",
                skill_capabilities=capabilities_str,
                has_examples="Yes" if has_examples else "No",
                has_triggers="Yes" if has_triggers else "No",
                has_workflow_steps="Yes" if has_workflow_steps else "No",
            )

            # Call LLM
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\[.*?\])\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\[.*?\])\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            questions = json.loads(response_text)

            if isinstance(questions, list) and len(questions) > 0:
                # Filter out questions that have already been asked
                new_questions = []
                for q in questions:
                    if not context.has_asked_question(q):
                        new_questions.append(q)
                        context.asked_questions.append(q)

                if new_questions:
                    logger.info(f"Generated {len(new_questions)} new contextual questions via LLM")
                    return new_questions[:3]  # Return max 3 questions
                else:
                    logger.info("All generated questions were already asked, using fallback")
                    # Fall through to template fallback

            # Fallback: generate generic questions based on missing context
            logger.warning("LLM returned invalid questions format, using generic fallback")
            return self._generate_fallback_questions(context)

        except Exception as e:
            logger.warning(f"Failed to generate clarifying questions: {e}, using generic fallback")
            # Emergency fallback to generic questions
            return self._generate_fallback_questions(context)

    def _generate_fallback_questions(self, context: ConversationContext) -> list[str]:
        """Generate fallback questions when LLM fails.

        Creates simple, generic questions based on what's missing in the context.

        Args:
            context: Current conversation context

        Returns:
            List of 2-3 generic clarifying questions
        """
        questions = []

        # Check what's missing and ask for it
        if not context.examples or len(context.examples) < 2:
            questions.append("Can you provide 2-3 specific examples of what this skill should do?")

        if not context.triggers:
            questions.append(
                "When should this skill be used? What situations or contexts trigger it?"
            )

        # Capability-specific questions
        if context.skill_capabilities:
            if context.skill_capabilities.needs_multi_step_workflow and not context.workflow_steps:
                questions.append("What are the main steps in this workflow, in order?")

            if context.skill_capabilities.needs_external_knowledge and not context.references_topics:
                questions.append("What topics or knowledge areas does this skill need to reference?")

            if context.skill_capabilities.needs_script_execution and not context.scripts_needed:
                questions.append("What scripts or commands need to be executed?")

        # If we don't have enough questions, add a generic one
        if len(questions) < 2:
            questions.append("Can you describe the expected behavior in more detail?")

        return questions[:3]  # Return max 3 questions

    async def attempt_inference_from_context(
        self,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Attempt to infer missing information from conversation context.

        Uses LLM to intelligently infer missing examples, triggers, or workflow steps
        based on the conversation history and skill purpose. This helps avoid asking
        unnecessary clarifying questions when information can be reasonably inferred.

        Args:
            context: Current conversation context

        Returns:
            Dictionary with inferred information and confidence level

        Examples:
            >>> context = ConversationContext(
            ...     skill_purpose="Format product names",
            ...     skill_pattern=SkillPattern.SIMPLE,
            ...     message_history=[{"role": "user", "content": "I need to format names"}]
            ... )
            >>> result = await gatherer.attempt_inference_from_context(context)
            >>> assert "examples" in result or "triggers" in result
        """
        try:
            # Build missing info summary
            missing_info = []
            if len(context.examples) == 0:
                missing_info.append("- Examples (input/output pairs)")
            if len(context.triggers) == 0:
                missing_info.append("- Triggers/contexts (when to use)")
            if (context.skill_capabilities and
                context.skill_capabilities.needs_multi_step_workflow and
                len(context.workflow_steps) == 0):
                missing_info.append("- Workflow steps")

            if not missing_info:
                logger.info("No missing information to infer")
                return {"inferred": False, "confidence": 1.0}

            # Format conversation history
            conversation_history = self._format_conversation_history(context.message_history)

            # Format capabilities for prompt
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

            # Build inference prompt
            prompt = INFERENCE_FROM_CONTEXT_PROMPT.format(
                conversation_history=conversation_history,
                skill_purpose=context.skill_purpose or "Not specified",
                skill_pattern=capabilities_str,
                examples="; ".join(context.examples) if context.examples else "None",
                triggers="; ".join(context.triggers) if context.triggers else "None",
                workflow_steps="; ".join(context.workflow_steps)
                if context.workflow_steps
                else "None",
                missing_info="\n".join(missing_info),
            )

            # Call LLM to infer
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            inference_result = json.loads(response_text)

            # Extract inferred information
            inferred: dict[str, Any] = {
                "inferred": False,
                "confidence": inference_result.get("confidence", 0.0),
                "reasoning": inference_result.get("reasoning", ""),
            }

            # Check if examples were inferred
            if (
                inference_result.get("examples") != "CANNOT_INFER"
                and isinstance(inference_result.get("examples"), list)
                and len(inference_result.get("examples", [])) > 0
            ):
                inferred["examples"] = inference_result["examples"]
                inferred["inferred"] = True

            # Check if triggers were inferred
            if (
                inference_result.get("triggers") != "CANNOT_INFER"
                and isinstance(inference_result.get("triggers"), list)
                and len(inference_result.get("triggers", [])) > 0
            ):
                inferred["triggers"] = inference_result["triggers"]
                inferred["inferred"] = True

            # Check if workflow steps were inferred
            if (
                inference_result.get("workflow_steps") != "CANNOT_INFER"
                and isinstance(inference_result.get("workflow_steps"), list)
                and len(inference_result.get("workflow_steps", [])) > 0
            ):
                inferred["workflow_steps"] = inference_result["workflow_steps"]
                inferred["inferred"] = True

            logger.info(
                f"Inference result: {inferred['inferred']} "
                f"(confidence: {inferred['confidence']:.2f})"
            )
            return inferred

        except Exception as e:
            logger.warning(f"Failed to infer from context: {e}")
            return {"inferred": False, "confidence": 0.0, "reasoning": str(e)}

    async def should_ask_clarification(
        self,
        context: ConversationContext,
        inference_result: dict[str, Any],
    ) -> bool:
        """Decide whether to ask clarifying questions or proceed with inference.

        Uses LLM to make an intelligent decision about whether clarification is truly
        needed or if the inferred information is sufficient to proceed.

        Args:
            context: Current conversation context
            inference_result: Result from attempt_inference_from_context

        Returns:
            True if clarification is needed, False if can proceed with inference

        Examples:
            >>> context = ConversationContext(
            ...     skill_purpose="Format product names",
            ...     examples=["PA -> Pro Analytics"]
            ... )
            >>> inference = {"inferred": True, "confidence": 0.8}
            >>> should_ask = await gatherer.should_ask_clarification(context, inference)
            >>> assert isinstance(should_ask, bool)
        """
        try:
            # Format capabilities for prompt
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

            # Build decision prompt
            prompt = SHOULD_ASK_CLARIFICATION_PROMPT.format(
                skill_purpose=context.skill_purpose or "Not specified",
                skill_pattern=capabilities_str,
                examples="; ".join(context.examples) if context.examples else "None",
                triggers="; ".join(context.triggers) if context.triggers else "None",
                workflow_steps="; ".join(context.workflow_steps)
                if context.workflow_steps
                else "None",
                inference_attempted=inference_result.get("inferred", False),
                inference_results=inference_result.get("reasoning", "No inference attempted"),
            )

            # Call LLM
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            decision = json.loads(response_text)
            should_ask = decision.get("should_ask", True)

            logger.info(
                f"Clarification decision: {should_ask} "
                f"(reason: {decision.get('reasoning', 'N/A')})"
            )
            return should_ask

        except Exception as e:
            logger.warning(f"Failed to decide on clarification: {e}, defaulting to asking")
            # On error, default to asking (conservative approach)
            return True

    def _format_conversation_history(self, message_history: list[dict[str, str]]) -> str:
        """Format conversation history for LLM prompt.

        Args:
            message_history: List of message dictionaries with 'role' and 'content'

        Returns:
            Formatted conversation history string
        """
        if not message_history:
            return "No previous conversation."

        formatted_messages = []
        for msg in message_history[-10:]:  # Use last 10 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted_messages.append(f"{role.upper()}: {content}")

        return "\n".join(formatted_messages)

    async def extract_requirements(
        self,
        user_response: str,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Extract structured requirements from user response using LLM.

        Uses LLM to intelligently parse user responses and extract examples,
        workflow steps, triggers, reference topics, and scripts in a structured format.

        Args:
            user_response: User's response message
            context: Current conversation context

        Returns:
            Dictionary with extracted requirements (examples, triggers, etc.)

        Examples:
            >>> context = ConversationContext(skill_pattern=SkillPattern.SIMPLE)
            >>> extracted = await gatherer.extract_requirements(
            ...     "Input: PA, Output: Pro Analytics. Use when writing docs.",
            ...     context
            ... )
            >>> assert "examples" in extracted
            >>> assert "triggers" in extracted
        """
        try:
            # Build capability-specific guidance
            capability_guidance = self._get_capability_guidance(context.skill_capabilities)

            # Format conversation history for context
            conversation_history = self._format_conversation_history(context.message_history)

            # Format capabilities string
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

            # Build extraction prompt
            prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(
                skill_purpose=context.skill_purpose or "Not specified",
                skill_patterns=capabilities_str,
                conversation_history=conversation_history,
                user_message=user_response,
                pattern_specific_guidance=capability_guidance,
            )

            # Call LLM to extract requirements
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            extracted_data = json.loads(response_text)

            # Build result dictionary with only non-empty fields
            extracted: dict[str, Any] = {}

            if extracted_data.get("examples") and len(extracted_data["examples"]) > 0:
                extracted["examples"] = extracted_data["examples"]

            if extracted_data.get("triggers") and len(extracted_data["triggers"]) > 0:
                extracted["triggers"] = extracted_data["triggers"]

            if extracted_data.get("workflow_steps") and len(extracted_data["workflow_steps"]) > 0:
                extracted["workflow_steps"] = extracted_data["workflow_steps"]

            if (
                extracted_data.get("references_topics")
                and len(extracted_data["references_topics"]) > 0
            ):
                extracted["references_topics"] = extracted_data["references_topics"]

            if extracted_data.get("scripts_needed") and len(extracted_data["scripts_needed"]) > 0:
                extracted["scripts_needed"] = extracted_data["scripts_needed"]

            logger.info(
                f"LLM extracted requirements: {list(extracted.keys())} "
                f"- {extracted_data.get('extraction_notes', 'N/A')}"
            )
            return extracted

        except Exception as e:
            logger.warning(f"Failed to extract requirements via LLM: {e}, returning empty dict")
            # Return empty dict on error rather than failing
            return {}

    def _get_capability_guidance(self, capabilities: SkillCapabilities | None) -> str:
        """Get capability-specific guidance for extraction.

        Args:
            capabilities: Detected skill capabilities (or None)

        Returns:
            Capability-specific guidance text for the LLM
        """
        if not capabilities:
            return """**General extraction:**
- Extract examples, triggers, and any structured information provided
- Look for concrete demonstrations of what the skill should do"""

        guidance_parts = []

        # Basic transformation (always relevant)
        guidance_parts.append("""**Basic extraction focus:**
- Prioritize extracting clear input/output examples
- Look for triggers about when to apply the skill
- Examples should show the before/after or input/output clearly""")

        if capabilities.needs_multi_step_workflow:
            guidance_parts.append("""**Workflow capability focus:**
- Extract sequential workflow steps in order
- Look for numbered steps or sequence indicators (first, then, next)
- Identify triggers for when to start the workflow
- Preserve step dependencies and order""")

        if capabilities.needs_external_knowledge:
            guidance_parts.append("""**External knowledge capability focus:**
- Extract knowledge domains and reference topics
- Look for mentions of documentation, guidelines, or reference materials
- Identify what types of questions this skill should answer
- Note any specific reference sources mentioned""")

        if capabilities.needs_script_execution:
            guidance_parts.append("""**Script execution capability focus:**
- Extract all scripts, commands, and code blocks
- Preserve exact command syntax
- Look for shell commands, CLI operations, or automation scripts
- Identify triggers for when to execute these scripts""")

        if capabilities.needs_file_operations:
            guidance_parts.append("""**File operations capability focus:**
- Identify which files need to be read or written
- Look for file paths, formats, or validation requirements
- Note any specific file manipulation needs""")

        return "\n\n".join(guidance_parts)

    def has_sufficient_context(self, context: ConversationContext) -> bool:
        """Check if we have enough info to generate skill based on capabilities.

        Args:
            context: Current conversation context

        Returns:
            True if sufficient context for generation, False otherwise

        Examples:
            >>> context = ConversationContext(
            ...     skill_purpose="Format product names",
            ...     examples=["Input: PA, Output: Pro Analytics"],
            ...     triggers=["writing documentation"]
            ... )
            >>> assert gatherer.has_sufficient_context(context) is True
        """
        # Check basic requirements
        if not context.skill_purpose or len(context.skill_purpose.strip()) < 5:
            logger.debug("Insufficient context: missing skill purpose")
            return False

        # Track requirements
        requirements_met = True

        # Basic requirements (all skills need examples or triggers)
        has_examples = len(context.examples) >= 1
        has_triggers = len(context.triggers) >= 1

        # If we have capabilities, check capability-specific requirements
        if context.skill_capabilities:
            caps = context.skill_capabilities

            # Workflow capability: need steps and triggers
            if caps.needs_multi_step_workflow:
                has_steps = len(context.workflow_steps) >= 2
                if not (has_steps and has_triggers):
                    logger.debug("Workflow capability: need steps and triggers")
                    requirements_met = False

            # External knowledge capability: need reference topics
            if caps.needs_external_knowledge:
                has_topics = len(context.references_topics) >= 1
                if not has_topics:
                    logger.debug("External knowledge capability: need reference topics")
                    requirements_met = False

            # Script execution capability: need scripts
            if caps.needs_script_execution:
                has_scripts = len(context.scripts_needed) >= 1
                if not has_scripts:
                    logger.debug("Script execution capability: need scripts")
                    requirements_met = False

            # File operations capability: baseline examples/triggers are enough

        # Baseline check: need examples or triggers
        if not requirements_met:
            return False

        if not (has_examples or has_triggers):
            logger.debug("Basic requirement: need examples or triggers")
            return False

        logger.info("Sufficient context for skill generation")
        return requirements_met

    async def generate_skill_name(self, context: ConversationContext) -> str:
        """Generate kebab-case skill name from purpose.

        Uses LLM to generate a valid skill name following Anthropic guidelines:
        - Kebab-case format
        - 1-64 characters
        - Starts with lowercase letter
        - Gerund form or descriptive noun

        Args:
            context: Current conversation context

        Returns:
            Generated skill name in kebab-case

        Examples:
            >>> context = ConversationContext(
            ...     skill_purpose="Format product names",
            ...     skill_pattern=SkillPattern.SIMPLE,
            ...     examples=["Input: PA, Output: Pro Analytics"]
            ... )
            >>> name = await gatherer.generate_skill_name(context)
            >>> assert re.match(r"^[a-z][a-z0-9-]*$", name)
            >>> assert len(name) <= 64
        """
        try:
            # Build examples summary
            examples_summary = (
                "; ".join(context.examples[:3]) if context.examples else "None provided"
            )

            # Format capabilities string
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

            prompt = SKILL_NAME_GENERATION_PROMPT.format(
                skill_purpose=context.skill_purpose or "Unknown",
                skill_pattern=capabilities_str,
                examples=examples_summary,
            )

            # Call LLM
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            response_json = json.loads(response_text)
            name: str = str(response_json.get("name", "")).strip()

            # Validate name format
            if name and re.match(r"^[a-z][a-z0-9-]*$", name) and len(name) <= 64:
                logger.info(f"Generated skill name: {name}")
                return name

            # If LLM didn't generate valid name, create one from purpose
            logger.warning("LLM generated invalid name, creating from purpose")
            return self._generate_name_from_purpose(context.skill_purpose or "unknown-skill")

        except Exception as e:
            logger.warning(f"Failed to generate skill name: {e}, creating from purpose")
            return self._generate_name_from_purpose(context.skill_purpose or "unknown-skill")

    def _generate_name_from_purpose(self, purpose: str) -> str:
        """Generate a simple kebab-case name from purpose string.

        Args:
            purpose: Skill purpose text

        Returns:
            Valid kebab-case skill name
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        name = purpose.lower()
        name = re.sub(r"[^a-z0-9]+", "-", name)
        name = re.sub(r"-+", "-", name)  # Remove multiple consecutive hyphens
        name = name.strip("-")  # Remove leading/trailing hyphens

        # Ensure it starts with a letter
        if not name or not name[0].isalpha():
            name = "skill-" + name

        # Truncate to 64 chars
        if len(name) > 64:
            name = name[:64].rstrip("-")

        return name or "unknown-skill"

    async def generate_description(self, context: ConversationContext) -> str:
        """Generate description in official format: third person, WHAT + WHEN.

        Uses LLM to generate a description following Anthropic guidelines:
        - Third person perspective
        - Describes WHAT the skill does
        - Includes WHEN to use it
        - 1-1024 characters

        Args:
            context: Current conversation context

        Returns:
            Generated skill description

        Examples:
            >>> context = ConversationContext(
            ...     skill_name="formatting-product-names",
            ...     skill_purpose="Format product abbreviations",
            ...     examples=["PA -> Pro Analytics"],
            ...     triggers=["writing documentation"]
            ... )
            >>> desc = await gatherer.generate_description(context)
            >>> assert len(desc) <= 1024
            >>> assert len(desc) >= 10
        """
        try:
            # Build context summaries
            examples_summary = (
                "; ".join(context.examples[:3]) if context.examples else "None provided"
            )
            triggers_summary = (
                "; ".join(context.triggers[:3]) if context.triggers else "General use"
            )

            # Format capabilities string
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

            prompt = DESCRIPTION_GENERATION_PROMPT.format(
                skill_name=context.skill_name or "unknown",
                skill_purpose=context.skill_purpose or "Unknown purpose",
                skill_pattern=capabilities_str,
                examples=examples_summary,
                triggers=triggers_summary,
            )

            # Call LLM
            response_text = ""
            async for chunk in self.llm_generator.generate_stream(prompt):
                response_text += chunk

            # Parse JSON response
            response_text = response_text.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            response_json = json.loads(response_text)
            description: str = str(response_json.get("description", "")).strip()

            # Validate description length
            if description and 1 <= len(description) <= 1024:
                logger.info(f"Generated description: {description[:100]}...")
                return description

            # If LLM didn't generate valid description, create one from purpose
            logger.warning("LLM generated invalid description, creating from purpose")
            return self._generate_description_from_purpose(context)

        except Exception as e:
            logger.warning(f"Failed to generate description: {e}, creating from purpose")
            return self._generate_description_from_purpose(context)

    def _generate_description_from_purpose(self, context: ConversationContext) -> str:
        """Generate a simple description from context.

        Args:
            context: Conversation context

        Returns:
            Simple skill description
        """
        purpose = context.skill_purpose or "Performs a specific task"

        # Add trigger context if available
        if context.triggers:
            trigger_text = context.triggers[0]
            description = f"{purpose}. Use when {trigger_text}."
        else:
            description = f"{purpose}."

        # Ensure it doesn't exceed max length
        if len(description) > 1024:
            description = description[:1020] + "..."

        return description

    def determine_required_tools(self, context: ConversationContext) -> list[str]:
        """Determine required tools based on capabilities and LLM suggestions.

        Uses LLM-suggested tools from capability analysis as the primary source,
        with fallback heuristics based on capabilities and requirements.

        Args:
            context: Current conversation context with capabilities and requirements

        Returns:
            List of tool names/scoped permissions (e.g., ["Read", "Bash(git:*)"])

        Examples:
            >>> context = ConversationContext()
            >>> context.skill_capabilities = SkillCapabilities(
            ...     needs_file_operations=True
            ... )
            >>> tools = gatherer.determine_required_tools(context)
            >>> assert "Read" in tools
        """
        tools = []

        # First, use LLM-suggested tools if available
        if context.skill_capabilities and context.skill_capabilities.suggested_tools:
            tools.extend(context.skill_capabilities.suggested_tools)
            logger.info(f"Using LLM-suggested tools: {context.skill_capabilities.suggested_tools}")

        # Fallback: determine tools from capabilities
        if not tools and context.skill_capabilities:
            caps = context.skill_capabilities

            # File operations capability
            if caps.needs_file_operations:
                tools.extend(["Read", "Write"])

            # External knowledge capability
            if caps.needs_external_knowledge:
                tools.extend(["Read", "Grep", "Glob"])

            # Multi-step workflow capability
            if caps.needs_multi_step_workflow:
                if "Read" not in tools:
                    tools.append("Read")
                if "Write" not in tools:
                    tools.append("Write")
                tools.append("Edit")

            # Script execution capability
            if caps.needs_script_execution:
                tools.append("Bash(python {baseDir}/scripts/*:*)")
                if "Read" not in tools:
                    tools.append("Read")
                if "Write" not in tools:
                    tools.append("Write")

        # Add script-specific tool scopes based on scripts_needed
        if context.scripts_needed:
            for script_desc in context.scripts_needed:
                script_lower = script_desc.lower()

                # Git operations
                if "git" in script_lower:
                    tools.append("Bash(git:*)")

                # NPM/Node operations
                if "npm" in script_lower or "node" in script_lower or "yarn" in script_lower:
                    tools.append("Bash(npm:*)")
                    tools.append("Bash(node:*)")

                # Python operations
                if "python" in script_lower or ".py" in script_lower:
                    if "Bash(python {baseDir}/scripts/*:*)" not in tools:
                        tools.append("Bash(python:*)")

                # Docker operations
                if "docker" in script_lower:
                    tools.append("Bash(docker:*)")

                # Curl/wget operations
                if "curl" in script_lower or "wget" in script_lower or "http" in script_lower:
                    tools.append("Bash(curl:*)")

        # Add search tools if references needed
        if context.references_topics:
            if "Grep" not in tools:
                tools.append("Grep")
            if "Glob" not in tools:
                tools.append("Glob")

        # Default fallback if no tools determined
        if not tools:
            tools = ["Read", "Write"]

        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)

        logger.info(f"Determined required tools: {unique_tools}")
        return unique_tools
