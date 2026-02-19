#!/usr/bin/env python3
"""
Automated script to create a Twitter trending topic summarizer skill.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.chat.llm_generator import LLMResponseGenerator


async def create_twitter_skill():
    """Create Twitter trending topic summarizer skill automatically."""
    print("\n" + "=" * 80)
    print(" " * 20 + "🚀 Creating Twitter Trending Topic Summarizer Skill 🚀")
    print("=" * 80 + "\n")

    # Initialize the skill creation agent
    print("🔧 Initializing agent...")
    try:
        import logging
        logging.basicConfig(level=logging.DEBUG)

        llm_generator = LLMResponseGenerator(temperature=0.7)
        agent = SkillCreationAgent(llm_generator)
        print("✅ Agent ready!\n")
        print(f"Using LLM model: {llm_generator._model if hasattr(llm_generator, '_model') else 'default'}\n")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
        print("Please check your LLM configuration (.env file) and try again.")
        return

    # Generate a unique session ID
    session_id = f"session-{uuid4().hex[:8]}"
    print(f"💬 Session ID: {session_id}\n")

    # Define the conversation flow
    messages = [
        {
            "user": "Create a Twitter trending topic summarizer skill",
            "description": "Initial request to create the skill"
        },
        {
            "user": """This skill should:
1. Fetch trending topics from Twitter API or web scraping
2. Analyze each trending topic
3. Generate a concise summary of what each topic is about
4. Present the summaries in a clear, organized format

The skill needs:
- Web access to fetch trending topics
- Ability to read and analyze web content
- Text processing for summarization
- Output formatting

The output should include:
- Topic name/hashtag
- Brief summary (2-3 sentences)
- Category (news, entertainment, sports, etc.)
- Engagement level (if available)""",
            "description": "Detailed specification of the skill"
        },
        {
            "user": """Here are the details:

1. Example input/output:
   - Input: User requests "Get trending topics"
   - Output:
     * #SuperBowl2026 - The championship game is underway with an unexpected upset in progress. Fans are reacting to controversial referee calls. (Category: Sports, Engagement: Very High - 2.5M tweets)
     * #NewAIModel - Tech company releases groundbreaking AI model. Early reviews show significant improvements over previous versions. (Category: Technology, Engagement: High - 850K tweets)
     * #MoviePremiere - Major blockbuster premieres tonight. Stars walk red carpet as fans await reviews. (Category: Entertainment, Engagement: Medium - 320K tweets)

2. Edge cases:
   - If a topic spans multiple categories, pick the most dominant one or use "Mixed"
   - If engagement data is unavailable, mark as "Unknown"
   - If scraping fails, provide error message and suggest alternatives
   - Limit to top 10 trending topics to keep output manageable

3. Workflow:
   - User triggers the skill with a simple command
   - Skill fetches current trending topics from Twitter (using web scraping or API)
   - For each topic, gather context and generate summary
   - Return formatted list of summaries
   - Process should complete within 30-60 seconds""",
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
            if "saved successfully" in response_text.lower() or "skill is ready" in response_text.lower():
                print("\n" + "🎉" * 40)
                print("✅ Twitter Trending Topic Summarizer skill created successfully!")
                print("🎉" * 40 + "\n")

                # Try to find the skill directory
                skills_dir = Path(__file__).parent.parent / "src" / "omniforge" / "skills"
                print(f"\n📁 Checking for skill files in: {skills_dir}")

                # Look for newly created skill directories
                if skills_dir.exists():
                    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
                    print(f"\n📂 Found {len(skill_dirs)} skill directories:")
                    for skill_dir in sorted(skill_dirs):
                        print(f"   • {skill_dir.name}")
                        # Check for common files
                        for file in ['skill.yaml', 'main.py', 'README.md']:
                            file_path = skill_dir / file
                            if file_path.exists():
                                print(f"     ✓ {file}")

                return True

        except Exception as e:
            print(f"\n❌ Error during message processing: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n⚠️  Skill creation process completed but did not receive success confirmation.")
    return False


def main():
    """Entry point for the script."""
    try:
        success = asyncio.run(create_twitter_skill())
        if success:
            print("\n✅ Script completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Script completed with warnings. Check output above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
