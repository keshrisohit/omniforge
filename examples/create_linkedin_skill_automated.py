#!/usr/bin/env python3
"""
Automated script to create a LinkedIn trending topic and posts summarizer skill.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.chat.llm_generator import LLMResponseGenerator


async def create_linkedin_skill():
    """Create LinkedIn trending topic and posts summarizer skill automatically."""
    print("\n" + "=" * 80)
    print(" " * 15 + "🚀 Creating LinkedIn Trending Topics & Posts Summarizer Skill 🚀")
    print("=" * 80 + "\n")

    # Initialize the skill creation agent
    print("🔧 Initializing agent...")
    try:
        llm_generator = LLMResponseGenerator(temperature=0.7)
        agent = SkillCreationAgent(llm_generator)
        print("✅ Agent ready!\n")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
        return

    # Generate a unique session ID
    session_id = f"session-{uuid4().hex[:8]}"
    print(f"💬 Session ID: {session_id}\n")

    # Define the conversation flow
    messages = [
        {
            "user": "Create a LinkedIn trending topic and posts summarizer skill",
            "description": "Initial request to create the skill"
        },
        {
            "user": """This skill should:
1. Fetch trending topics and popular posts from LinkedIn
2. Analyze each trending topic and post
3. Generate concise summaries of what each topic/post is about
4. Identify key insights, engagement metrics, and professional relevance
5. Present the summaries in a clear, organized format

The skill needs:
- Web access to fetch LinkedIn trending topics and posts
- Ability to read and analyze LinkedIn content
- Text processing for summarization
- Engagement metrics analysis
- Output formatting

The output should include:
- Topic/Post title
- Author/Company (if applicable)
- Brief summary (2-3 sentences)
- Key insights or takeaways
- Category (career advice, industry news, tech trends, leadership, etc.)
- Engagement level (likes, comments, shares)
- Professional relevance score""",
            "description": "Detailed specification of the skill"
        },
        {
            "user": """Here are the details:

1. Example input/output:
   - Input: User requests "Get LinkedIn trending topics and posts"
   - Output:
     * Post: "The Future of AI in Enterprise" by John Smith (Tech CEO)
       - Summary: Discussion of how AI is transforming enterprise software. Author shares insights from implementing AI in Fortune 500 companies. Emphasizes need for ethical AI frameworks.
       - Key Insights: AI adoption accelerating, ethical considerations crucial, need for skilled workforce
       - Category: Technology Trends
       - Engagement: High - 12.5K likes, 890 comments, 2.3K shares
       - Relevance: High for tech leaders and professionals

     * Topic: #RemoteWork trends
       - Summary: Multiple posts discussing hybrid work models and productivity challenges. Common themes include work-life balance and team collaboration tools.
       - Key Insights: Hybrid models becoming standard, focus on async communication, mental health awareness
       - Category: Workplace Culture
       - Engagement: Very High - trending with 45K+ interactions
       - Relevance: High for managers and HR professionals

2. Edge cases:
   - If a post/topic spans multiple categories, pick the most dominant one or use "Mixed"
   - If engagement data is unavailable, mark as "Unknown"
   - If scraping fails or authentication is required, provide error message with alternatives
   - Limit to top 15-20 trending items to keep output manageable
   - Handle sponsored content appropriately

3. Workflow:
   - User triggers the skill with a simple command
   - Skill fetches current trending topics and popular posts from LinkedIn
   - For each item, gather context and generate summary with key insights
   - Analyze engagement metrics and professional relevance
   - Return formatted list of summaries
   - Process should complete within 45-90 seconds

4. Additional features:
   - Filter by category (optional: tech, leadership, career, industry news)
   - Sort by engagement or relevance
   - Extract actionable insights for professionals""",
            "description": "Additional details with examples and edge cases"
        },
        {
            "user": "yes",
            "description": "Confirmation to proceed with skill creation"
        }
    ]

    # Process each message in the conversation
    for i, message in enumerate(messages, 1):
        print(f"\n{'=' * 80}")
        print(f"Message {i}/{len(messages)}: {message['description']}")
        print(f"{'=' * 80}\n")
        print(f"You: {message['user'][:100]}{'...' if len(message['user']) > 100 else ''}\n")

        # Stream the agent's response
        print("🤖 Agent: ", end="", flush=True)
        response_text = ""

        try:
            async for chunk in agent.handle_message(message['user'], session_id):
                print(chunk, end="", flush=True)
                response_text += chunk
            print("\n")

            # Check if skill was created
            if "saved successfully" in response_text.lower() or "success!" in response_text.lower():
                print("\n" + "🎉" * 40)
                print("✅ LinkedIn Trending Topics & Posts Summarizer skill created successfully!")
                print("🎉" * 40 + "\n")

                # Find the skill directory
                skills_dir = Path(__file__).parent.parent / "src" / "omniforge" / "skills"
                print(f"\n📁 Checking for skill files in: {skills_dir}")

                # Look for the newly created skill
                if skills_dir.exists():
                    skill_dirs = [d for d in skills_dir.iterdir()
                                 if d.is_dir() and 'linkedin' in d.name.lower()]
                    if skill_dirs:
                        print(f"\n📂 Found LinkedIn skill directory:")
                        for skill_dir in skill_dirs:
                            print(f"\n   Skill: {skill_dir.name}")
                            # List all files
                            for file in skill_dir.rglob('*'):
                                if file.is_file():
                                    rel_path = file.relative_to(skill_dir)
                                    size = file.stat().st_size
                                    print(f"     ✓ {rel_path} ({size} bytes)")

                return True

        except Exception as e:
            print(f"\n❌ Error during message processing: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n⚠️  Skill creation process completed.")
    return False


def main():
    """Entry point for the script."""
    try:
        success = asyncio.run(create_linkedin_skill())
        if success:
            print("\n✅ Script completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Script completed. Check output above.")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
