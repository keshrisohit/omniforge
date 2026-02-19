# Scripts

This folder contains utility scripts for development, testing, and data seeding.

## Available Scripts

### `seed_data.py`

Seeds the in-memory repositories with sample agents for testing different scenarios.

**Usage:**
```bash
python -m scripts.seed_data
```

**What it does:**
- Creates 5 different sample agents with various capabilities:
  - **Data Analysis Agent** - Analytics and visualization
  - **Code Generation Agent** - Code generation and review
  - **Content Writing Agent** - Blog posts and marketing copy
  - **Research Agent** - Web research and fact-checking
  - **Customer Support Agent** - Customer inquiries and ticket management

- Each agent has different skills and capabilities (streaming, multi-turn, HITL, push notifications)
- Demonstrates agent registration and discovery by skills/tags
- Returns seeded repositories for use in tests

**Integration in Tests:**

```python
from scripts.seed_data import seed_agents

async def test_my_feature():
    # Get pre-seeded repositories
    registry, task_repo = await seed_agents()

    # Use them in your tests
    agent = await registry.get("data-analysis-agent")
    assert agent.identity.name == "Data Analysis Agent"
```

## Creating New Seed Scripts

When creating additional seed scripts:

1. Follow the naming convention: `seed_<entity>.py`
2. Provide a main async function that returns the seeded repositories
3. Include helpful console output showing what was seeded
4. Add documentation to this README

## Testing Scenarios Covered

The current seed data supports testing:

- ✅ Agent registration and discovery
- ✅ Finding agents by skill ID
- ✅ Finding agents by tag
- ✅ Multi-tenant scenarios (add tenant_id when creating agents)
- ✅ Different capability combinations
- ✅ Various input/output modes
- ✅ Task processing with different agent types

## Future Scripts

Consider adding scripts for:

- Database migration/seeding for production databases
- Performance testing data generation
- User and authentication seeding
- Integration test fixtures
