"""Conversation prompts for agent creation."""

from typing import Optional


def initial_prompt() -> str:
    """Get initial greeting prompt.

    Returns:
        Initial greeting message
    """
    return (
        "Hi! I'll help you create an AI agent that automates your work.\n\n"
        "What would you like to automate?"
    )


def understanding_goal_prompt(goal: str) -> str:
    """Get prompt for understanding the goal.

    Args:
        goal: User's stated goal

    Returns:
        Response asking for integration
    """
    return (
        f"Got it! You want to automate: '{goal}'\n\n"
        "To create this agent, I'll need to connect to your integrations. "
        "Which service should this agent use? (e.g., Notion, Slack, Linear)"
    )


def integration_setup_prompt(integration: str) -> str:
    """Get prompt for setting up integration.

    Args:
        integration: Integration type

    Returns:
        Response about connecting integration
    """
    return (
        f"Perfect! I'll help you set up {integration.capitalize()}.\n\n"
        f"To connect {integration.capitalize()}, I need you to authorize access. "
        "This is a one-time setup. Ready to connect?"
    )


def integration_connected_prompt(integration: str) -> str:
    """Get prompt after integration is connected.

    Args:
        integration: Integration type

    Returns:
        Response confirming connection
    """
    return (
        f"{integration.capitalize()} connected successfully!\n\n"
        "Now, tell me more about what this agent should do:\n"
        "- What information should it gather?\n"
        "- What format should the output be?\n"
        "- When should it run?"
    )


def multi_skill_suggestion_prompt(
    suggested_flow: str,
    public_skills: Optional[list[dict[str, str]]] = None,
) -> str:
    """Get prompt suggesting multi-skill composition.

    Args:
        suggested_flow: Plain language description of the flow
        public_skills: Optional list of suggested public skills

    Returns:
        Response suggesting skill composition
    """
    lines = [
        "I'll create an agent that:",
        "",
        suggested_flow,
        "",
    ]

    if public_skills and len(public_skills) > 0:
        lines.append("I found some existing skills you can use:")
        lines.append("")
        for skill in public_skills:
            lines.append(f"- **{skill['name']}**: {skill['description']}")
        lines.append("")
        lines.append("Would you like to use these, or should I create custom skills?")
    else:
        lines.append("Does this sound right? I'll create custom skills for each step.")

    return "\n".join(lines)


def skill_design_summary_prompt(
    goal: str,
    integration: str,
    trigger: str,
    num_skills: int,
) -> str:
    """Get prompt summarizing skill design.

    Args:
        goal: Agent goal
        integration: Integration type
        trigger: Trigger type
        num_skills: Number of skills

    Returns:
        Summary prompt
    """
    skill_text = "skill" if num_skills == 1 else f"{num_skills} skills"

    return (
        "Let me summarize what I understood:\n\n"
        f"**Agent Purpose**: {goal}\n"
        f"**Integration**: {integration}\n"
        f"**Skills**: {skill_text}\n"
        f"**Trigger**: {trigger}\n\n"
        "Does this look correct? (yes/no)"
    )


def testing_prompt() -> str:
    """Get prompt for testing phase.

    Returns:
        Testing prompt
    """
    return (
        "Great! I've designed the skills for your agent.\n\n"
        "Before activating it, let's test it with sample data. "
        "Want me to run a test now? (yes/no)"
    )


def test_success_prompt() -> str:
    """Get prompt after successful test.

    Returns:
        Test success prompt
    """
    return (
        "Test completed successfully!\n\n"
        "Your agent is ready to deploy. "
        "Should I activate it now? (yes/no)"
    )


def deployment_success_prompt(
    agent_name: str,
    trigger: str,
    schedule: Optional[str],
) -> str:
    """Get prompt after successful deployment.

    Args:
        agent_name: Name of the agent
        trigger: Trigger type
        schedule: Schedule if applicable

    Returns:
        Deployment success prompt
    """
    schedule_text = schedule or "On-demand"

    return (
        f"Your '{agent_name}' agent is now active!\n\n"
        f"**Trigger**: {trigger}\n"
        f"**Schedule**: {schedule_text}\n\n"
        "You can manage this agent from your dashboard."
    )


def modification_prompt() -> str:
    """Get prompt when user wants to modify.

    Returns:
        Modification prompt
    """
    return "No problem! Tell me what needs to be changed."


def wait_for_connection_prompt() -> str:
    """Get prompt when waiting for connection.

    Returns:
        Wait prompt
    """
    return "No problem! Let me know when you're ready to connect."


def wait_for_test_prompt() -> str:
    """Get prompt when waiting for test confirmation.

    Returns:
        Wait prompt
    """
    return "No problem! Let me know when you're ready to test."


def draft_saved_prompt() -> str:
    """Get prompt when agent saved as draft.

    Returns:
        Draft saved prompt
    """
    return "No problem! Your agent is saved as a draft. You can activate it later."


def public_skill_options_prompt(skills: list[dict[str, str]]) -> str:
    """Get prompt showing public skill options.

    Args:
        skills: List of public skills with name and description

    Returns:
        Formatted skill options
    """
    lines = ["I found these existing skills that might help:", ""]

    for i, skill in enumerate(skills, 1):
        lines.append(f"{i}. **{skill['name']}**")
        lines.append(f"   {skill['description']}")
        lines.append("")

    lines.append("Would you like to use any of these? (Enter numbers like '1,3' or 'none')")

    return "\n".join(lines)


def mixed_skills_confirmation_prompt(
    public_skills: list[str],
    custom_skills: list[str],
) -> str:
    """Get prompt confirming mixed public and custom skills.

    Args:
        public_skills: Names of public skills to use
        custom_skills: Descriptions of custom skills to create

    Returns:
        Confirmation prompt
    """
    lines = ["Great! I'll set up your agent with:", ""]

    if public_skills:
        lines.append("**Existing Skills:**")
        for skill in public_skills:
            lines.append(f"- {skill}")
        lines.append("")

    if custom_skills:
        lines.append("**Custom Skills I'll Create:**")
        for skill in custom_skills:
            lines.append(f"- {skill}")
        lines.append("")

    lines.append("Does this look right? (yes/no)")

    return "\n".join(lines)


def skill_order_confirmation_prompt(skills_in_order: list[str]) -> str:
    """Get prompt confirming skill execution order.

    Args:
        skills_in_order: Skill names in execution order

    Returns:
        Order confirmation prompt
    """
    lines = ["I'll run the skills in this order:", ""]

    for i, skill in enumerate(skills_in_order, 1):
        lines.append(f"{i}. {skill}")

    lines.append("")
    lines.append("Is this order correct? (yes/no, or tell me the correct order)")

    return "\n".join(lines)
