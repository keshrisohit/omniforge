# Multi-Skill Agent Demo

This demo showcases how OmniForge agents can dynamically use multiple skills based on user prompts to accomplish complex tasks.

## Overview

The demo includes:

1. **Two Skills**:
   - `data-processor`: Analyzes and processes data from files
   - `report-generator`: Creates professional reports from analysis results

2. **Sample Agent**:
   - `AnalystAgent`: An intelligent agent that uses skills dynamically

3. **Demo Scripts**:
   - `analyst_agent.py`: Simple agent implementation showing skill selection
   - `full_demo.py`: Complete end-to-end demonstration with real skill loading

## Skills

### data-processor

**Location**: `src/omniforge/skills/data-processor/SKILL.md`

**Purpose**: Process and analyze data from various sources

**Allowed Tools**: Read, Glob, Bash

**Capabilities**:
- Read data from CSV, JSON, text files
- Filter and aggregate data
- Perform statistical analysis
- Validate data quality

### report-generator

**Location**: `src/omniforge/skills/report-generator/SKILL.md`

**Purpose**: Generate professional reports from analysis results

**Allowed Tools**: Write, Edit, Read

**Capabilities**:
- Create structured reports with sections
- Format data as tables and lists
- Generate executive summaries
- Provide insights and recommendations

## Running the Demo

### Quick Demo (Simple Agent)

```bash
cd examples/multi_skill_demo
python analyst_agent.py
```

This shows how the agent determines which skills to use based on the prompt.

### Full Demo (Complete Workflow)

```bash
cd examples/multi_skill_demo
python full_demo.py
```

This demonstrates:
- Skill discovery and loading
- Multi-skill orchestration
- Tool restrictions enforcement
- Progressive disclosure pattern
- Creating sample data and generating reports

## How Multi-Skill Works

### 1. Skill Discovery

The agent uses `SkillLoader` to discover available skills:

```python
from omniforge.skills.loader import SkillLoader
loader = SkillLoader(storage_config=storage_config)
skills = loader.list_skills()
```

### 2. Dynamic Selection

Based on the user's prompt, the agent determines which skills are needed:

```python
# Example prompt: "Analyze sales data and create a report"
# Agent reasoning:
# - "analyze" → needs data-processor skill
# - "create a report" → needs report-generator skill
# - Decision: Use both skills sequentially
```

### 3. Skill Activation

The agent loads the full skill content when needed:

```python
skill = loader.load_skill("data-processor")
# Now the agent has the full skill instructions and tool restrictions
```

### 4. Tool Execution with Restrictions

Each skill specifies which tools it can use:

```python
# data-processor can only use: Read, Glob, Bash
# report-generator can only use: Write, Edit, Read
# ToolExecutor enforces these restrictions
```

### 5. Multi-Skill Orchestration

For complex tasks, the agent coordinates multiple skills:

```
User Request: "Analyze Q1 sales and generate a report"
    ↓
Step 1: Activate data-processor skill
    ↓
    - Read sales data file
    - Calculate metrics
    - Identify trends
    ↓
Step 2: Activate report-generator skill
    ↓
    - Take analysis results
    - Format as professional report
    - Write report file
    ↓
Final Output: sales_report.md
```

## Example Prompts

Try these prompts to see different skill combinations:

### Single Skill (data-processor only)
- "Analyze the sales data from Q1"
- "Calculate the average revenue by region"
- "Find all transactions above $1000"

### Single Skill (report-generator only)
- "Generate an executive summary"
- "Create a report template"
- "Format the analysis as a professional document"

### Multi-Skill (both)
- "Analyze Q2 data and create a comprehensive report"
- "Process customer feedback and generate insights report"
- "Review sales trends and write a summary document"

## Architecture Benefits

### 1. Modularity
Skills are independent and reusable across different agents

### 2. Security
Tool restrictions prevent skills from performing unintended actions

### 3. Composability
Multiple skills can be combined to handle complex workflows

### 4. Efficiency
Progressive disclosure loads skill content only when needed

### 5. Maintainability
Skills can be updated independently without changing agents

## Next Steps

To extend this demo:

1. **Add More Skills**: Create additional skills for specialized tasks
2. **Real LLM Integration**: Use an LLM to intelligently select skills
3. **Parallel Execution**: Execute independent skills concurrently
4. **Skill Chaining**: Pass outputs between skills automatically
5. **Error Handling**: Add retry logic and fallback strategies

## Files Generated

When you run `full_demo.py`, it creates:

```
examples/multi_skill_demo/demo_data/
├── sales_data.json      # Sample sales data
└── sales_report.md      # Generated report
```

## Learn More

- Skills System: `src/omniforge/skills/`
- Agent Base Classes: `src/omniforge/agents/`
- Tool Execution: `src/omniforge/tools/executor.py`
- Multi-Skill Tests: `tests/builder/conversation/test_multi_skill.py`
