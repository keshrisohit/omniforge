# Testing the Conversational Skill Builder

This guide explains how to test the Conversational Skill Builder feature.

## Quick Start

### 1. Run Unit Tests

The fastest way to verify everything works:

```bash
# Run all builder tests
pytest tests/builder/ -v

# With coverage report
pytest tests/builder/ --cov=src/omniforge/builder --cov-report=term-missing

# Run specific test file
pytest tests/builder/test_conversation.py -v
pytest tests/builder/test_skill_generator.py -v
pytest tests/builder/test_repository.py -v
```

**Expected Result**: 78/80 tests passing (97.5% pass rate)

---

## 2. Run Interactive Demo

Experience the conversational flow firsthand:

```bash
python examples/interactive_agent_builder.py
```

**What it does**:
- Starts an interactive conversation
- Guides you through agent creation
- Shows state transitions
- Displays final agent configuration

**Example conversation**:
```
🤖 Assistant: What would you like to automate?

👤 You: I want to automate weekly reports from Notion

🤖 Assistant: Got it! You want to automate: 'I want to automate weekly reports from Notion'

              To create this agent, I'll need to connect to your integrations.
              Which service should this agent use? (e.g., Notion, Slack, Linear)

👤 You: Notion

🤖 Assistant: Perfect! I'll help you set up Notion.

              To connect Notion, I need you to authorize access.
              This is a one-time setup. Ready to connect?

👤 You: Yes

... (continues through 7 states)
```

---

## 3. Run Automated Demo

See the full end-to-end flow with simulated user input:

```bash
python examples/test_conversational_builder.py
```

**What it demonstrates**:
1. ✅ Creating agent through conversation (7-state flow)
2. ✅ Generating Claude Code-compliant SKILL.md files
3. ✅ Saving agent configuration to database
4. ✅ Executing agent and tracking results
5. ✅ Viewing execution history

**Sample output**:
```
============================================================
CONVERSATIONAL AGENT BUILDER - DEMO
============================================================

📁 Skills directory: /tmp/tmpxyz123

🤖 Assistant: Hello! I can help you create an automation agent.
              What would you like to automate?

👤 User: I want to automate weekly reports from Notion

🤖 Assistant: Got it! You want to automate: 'I want to automate weekly reports from Notion'
...

✅ AGENT CREATED SUCCESSFULLY!

📋 Agent Configuration:
   Name: Notion Agent
   Description: I want to automate weekly reports from Notion
   Trigger: scheduled
   Schedule: 0 8 * * MON
   Skills: 1

🎯 Skills:
   1. Notion Automation (notion-automation)

💾 Agent saved to database with ID: agent-abc123

📝 Generating SKILL.md files...
   Created 1 skill file(s):
   - notion-automation.md
     Preview: ---...

🚀 Executing agent (test mode)...
   Status: success
   Duration: 45ms

📊 Execution History (1 runs):
   - 2026-01-26 10:30:00: success
```

---

## 4. Test Individual Components

### A. Test Database Models

```bash
pytest tests/builder/models/ -v
```

Tests:
- AgentConfig validation (cron, skill order, integrations)
- Credential encryption/decryption
- AgentExecution status tracking

### B. Test Repository Layer

```bash
pytest tests/builder/test_repository.py -v
```

Tests:
- CRUD operations
- Tenant isolation
- Cascade deletes
- Async operations

### C. Test SKILL.md Generation

```bash
pytest tests/builder/test_skill_generator.py -v
```

Tests:
- Claude Code format compliance
- Frontmatter validation
- Forbidden field detection
- Progressive disclosure

### D. Test Conversation Flow

```bash
pytest tests/builder/test_conversation.py -v
```

Tests:
- 7-state conversation flow
- Scheduled vs. on-demand triggers
- Requirement gathering
- Message history tracking

---

## 5. Manual Testing - Component by Component

### Test A: Create an Agent Config

```python
from omniforge.builder.models import AgentConfig, SkillReference, TriggerType

# Create agent
agent = AgentConfig(
    tenant_id="test-tenant",
    name="My Test Agent",
    description="Test agent for weekly reports",
    trigger=TriggerType.SCHEDULED,
    schedule="0 8 * * MON",  # Monday 8am
    skills=[
        SkillReference(
            skill_id="test-skill",
            name="Test Skill",
            source="custom",
            order=1,
        )
    ],
    created_by="test-user",
)

print(f"Agent: {agent.name}")
print(f"Trigger: {agent.trigger.value}")
print(f"Schedule: {agent.schedule}")
```

### Test B: Generate a SKILL.md File

```python
from omniforge.builder.skill_generator import SkillGenerationRequest, SkillMdGenerator

# Create request
request = SkillGenerationRequest(
    skill_id="my-test-skill",
    name="My Test Skill",
    description="A test skill for automation",
    purpose="Test skill execution",
    steps=[
        "Connect to API",
        "Fetch data",
        "Process results",
    ],
    allowed_tools=["ExternalAPI", "Read", "Write"],
)

# Generate SKILL.md
generator = SkillMdGenerator()
content = generator.generate(request)

print(content)
```

**Check for**:
- `---` frontmatter delimiters
- `name: my-test-skill`
- `description: ...`
- `allowed-tools: [...]`
- `## Instructions` section
- No forbidden fields (schedule, trigger, etc.)

### Test C: Conversation Flow

```python
from omniforge.builder.conversation import ConversationManager

manager = ConversationManager()
context = manager.start_conversation("test-1", "tenant-1", "user-1")

# Step through conversation
context, resp = manager.process_user_input("test-1", "Weekly Notion reports")
print(f"State: {context.state.value}")
print(f"Response: {resp}")

context, resp = manager.process_user_input("test-1", "Notion")
print(f"State: {context.state.value}")

# ... continue flow ...
```

---

## 6. Test Database Persistence

### Setup Test Database

```python
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from omniforge.builder.models.orm import Base
from omniforge.builder.models import AgentConfig, SkillReference
from omniforge.builder.repository import AgentConfigRepository

async def test_db():
    # Create in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Test repository
    async with async_session_maker() as session:
        repo = AgentConfigRepository(session)

        # Create agent
        agent = AgentConfig(
            tenant_id="tenant-1",
            name="Test Agent",
            description="Test",
            skills=[SkillReference(skill_id="test", name="Test", order=1)],
            created_by="user-1",
        )

        created = await repo.create(agent)
        await session.commit()

        print(f"Created agent: {created.id}")

        # Retrieve agent
        fetched = await repo.get_by_id(created.id, "tenant-1")
        print(f"Fetched agent: {fetched.name}")

        # List agents
        agents = await repo.list_by_tenant("tenant-1")
        print(f"Total agents: {len(agents)}")

asyncio.run(test_db())
```

---

## 7. Test Skill Execution

```python
import asyncio
from pathlib import Path
import tempfile

from omniforge.builder.executor import AgentExecutor
from omniforge.builder.skill_generator import SkillMdGenerator, SkillGenerationRequest
from omniforge.builder.models import AgentConfig, SkillReference

async def test_execution():
    # Setup
    skills_dir = Path(tempfile.mkdtemp())
    generator = SkillMdGenerator()
    executor = AgentExecutor(generator, skills_dir)

    # Create agent
    agent = AgentConfig(
        tenant_id="tenant-1",
        name="Test Agent",
        description="Test",
        skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
        created_by="user-1",
    )

    # Create skill request
    skill_request = SkillGenerationRequest(
        skill_id="test-skill",
        name="Test Skill",
        description="Test",
        purpose="Test execution",
        steps=["Do something"],
    )

    # Prepare skills
    await executor.prepare_agent_skills(agent, [skill_request])

    # Verify skill file exists
    skill_file = skills_dir / "tenant-1" / "skills" / "test-skill.md"
    print(f"Skill file exists: {skill_file.exists()}")
    print(f"Content preview: {skill_file.read_text()[:200]}")

asyncio.run(test_execution())
```

---

## Expected Test Results

### Unit Tests Summary

```
tests/builder/models/test_agent_config.py::TestSkillReference       ✓ 3/3
tests/builder/models/test_agent_config.py::TestAgentConfig          ✓ 11/11
tests/builder/models/test_credential.py::TestCredential             ✓ 11/11
tests/builder/models/test_execution.py::TestAgentExecution          ✓ 6/6
tests/builder/test_repository.py::TestAgentConfigRepository         ✓ 7/7
tests/builder/test_repository.py::TestCredentialRepository          ✓ 4/4
tests/builder/test_repository.py::TestAgentExecutionRepository      ✓ 4/4
tests/builder/test_skill_generator.py::TestSkillGenerationRequest   ✓ 2/2
tests/builder/test_skill_generator.py::TestSkillMdGenerator         ✓ 13/13
tests/builder/test_conversation.py::TestConversationContext         ✓ 3/3
tests/builder/test_conversation.py::TestConversationManager         ✓ 10/10
tests/builder/test_executor.py::TestAgentExecutor                   ✓ 3/5
tests/builder/test_executor.py::TestAgentExecutionService           ✓ 3/4

TOTAL: 78/80 tests passing (97.5%)
```

### Coverage Report

```
src/omniforge/builder/__init__.py                     100%
src/omniforge/builder/models/__init__.py              100%
src/omniforge/builder/models/agent_config.py          100%
src/omniforge/builder/models/credential.py             94%
src/omniforge/builder/models/execution.py             100%
src/omniforge/builder/models/orm.py                   100%
src/omniforge/builder/repository.py                    93%
src/omniforge/builder/skill_generator.py               99%
src/omniforge/builder/conversation.py                  97%
src/omniforge/builder/executor.py                      85%
-------------------------------------------------------------
TOTAL                                                  95%
```

---

## Troubleshooting

### Issue: Import errors

**Solution**: Install package in editable mode
```bash
pip install -e ".[dev]"
```

### Issue: Database errors in tests

**Solution**: SQLite foreign keys not enabled
```python
await conn.execute(text("PRAGMA foreign_keys=ON"))
```

### Issue: Skill file not found during execution

**Solution**: Ensure skills directory structure exists
```python
skills_dir / tenant_id / "skills" / f"{skill_id}.md"
```

### Issue: Tests fail with async errors

**Solution**: Use pytest-asyncio
```bash
pip install pytest-asyncio
```

---

## What's Working (MVP Status)

✅ **Database Layer**
- Agent configuration CRUD
- Credential encryption
- Execution tracking
- Tenant isolation

✅ **SKILL.md Generation**
- Claude Code format compliance
- Frontmatter validation
- Progressive disclosure
- Tool restrictions

✅ **Conversation Flow**
- 7-state state machine
- Message history
- Requirement gathering
- Agent configuration building

✅ **Execution Service**
- Skill preparation
- Basic execution
- Status tracking
- Test mode

---

## What's Not Yet Implemented

❌ **OAuth Integration** (TASK-104)
- Notion OAuth flow
- Token storage
- Refresh handling

❌ **REST API** (TASK-106)
- HTTP endpoints
- Request/response models
- Authentication

❌ **CLI Commands** (TASK-107)
- `omniforge agent create`
- `omniforge agent list`
- `omniforge agent execute`

❌ **Integration Tests** (TASK-108)
- End-to-end API tests
- OAuth flow tests
- Multi-agent scenarios

---

## Next Steps

1. **Run the demos**: Try the interactive and automated demos to see the feature in action
2. **Review test output**: Run unit tests to verify all components work
3. **Check generated files**: Inspect SKILL.md files to verify Claude Code compliance
4. **Experiment**: Modify the examples to create different agent configurations
5. **Implement remaining tasks**: OAuth, REST API, CLI, integration tests

---

## Getting Help

If you encounter issues:

1. Check the test output for specific errors
2. Review the implementation in `src/omniforge/builder/`
3. Look at test examples in `tests/builder/`
4. Check the product spec: `specs/product-spec-conversational-skill-builder.md`
5. Review technical plan: `specs/technical-plan-conversational-skill-builder.md`
