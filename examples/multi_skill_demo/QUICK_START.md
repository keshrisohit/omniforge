# Multi-Skill Agent Demo - Quick Start Guide

## 🎯 What This Demonstrates

An intelligent analyst agent that **dynamically selects and uses multiple skills** based on user prompts to accomplish complex tasks.

## 📦 What Was Created

### Skills (in `src/omniforge/skills/`)
1. **data-processor** - Analyzes data from files (Read, Glob, Bash)
2. **report-generator** - Creates professional reports (Write, Edit, Read)

### Demo Scripts (in `examples/multi_skill_demo/`)
1. **analyst_agent_simple.py** - Conceptual demo (easiest to understand)
2. **full_demo.py** - Complete end-to-end workflow with real output
3. **analyst_agent.py** - Full agent implementation

### Documentation
- **README.md** - Detailed documentation
- **SUMMARY.md** - Technical summary with fixes
- **QUICK_START.md** - This file!

## 🚀 Run the Demo

### Option 1: Simple Concept Demo (Recommended for Understanding)
```bash
python examples/multi_skill_demo/analyst_agent_simple.py
```

**Shows:**
- How agent analyzes prompts
- Which skills get selected
- Decision-making process

**Output Example:**
```
TEST 3: Analyze Q2 data and create a comprehensive report
============================================================

🎯 DECISION: Use BOTH skills sequentially
   1️⃣  data-processor (analyze data)
   2️⃣  report-generator (create report)

💡 In a real implementation:
   • Load data-processor skill via SkillTool
   • Execute with Read, Glob, Bash tools (restricted)
   • Load report-generator skill via SkillTool
   • Execute with Write, Edit, Read tools (restricted)
   • Return final report to user
```

### Option 2: Full Workflow Demo (See It In Action)
```bash
python examples/multi_skill_demo/full_demo.py
```

**Shows:**
- Skill discovery and indexing
- Loading skills with metadata
- Multi-skill workflow execution
- Tool restrictions enforcement
- Actual file generation

**Output:**
- Creates `demo_data/sales_data.json`
- Generates `demo_data/sales_report.md`

## 💡 Example Prompts and Skill Selection

| User Prompt | Skills Used | Why |
|------------|-------------|-----|
| "Analyze sales data from Q1" | `data-processor` only | Contains "analyze" and "data" |
| "Generate a customer report" | `report-generator` only | Contains "generate" and "report" |
| "Analyze Q2 data and create a report" | BOTH skills | Contains both analysis and reporting keywords |
| "Help me with something" | None (asks for clarification) | No clear skill indicators |

## 🔍 How It Works

### 1. Skill Discovery
```python
# Agent discovers available skills
loader = SkillLoader(config=storage_config)
loader.build_index()
skills = loader.list_skills()  # ['data-processor', 'report-generator']
```

### 2. Prompt Analysis
```python
# Agent analyzes user prompt
prompt = "Analyze Q2 data and create a comprehensive report"

needs_data_processing = "analyze" in prompt and "data" in prompt  # True
needs_report = "report" in prompt  # True

# Decision: Use BOTH skills
```

### 3. Skill Loading
```python
# Load skills on demand
data_skill = loader.load_skill("data-processor")
# Returns: Full skill content + allowed tools

report_skill = loader.load_skill("report-generator")
# Returns: Full skill content + allowed tools
```

### 4. Sequential Execution
```
Step 1: data-processor skill
  ↓ Read sales_data.json (allowed)
  ↓ Analyze metrics
  ↓ Output: analysis_results

Step 2: report-generator skill
  ↓ Take analysis_results
  ↓ Write sales_report.md (allowed)
  ↓ Output: Professional report
```

## 🔒 Tool Restrictions (Security)

Each skill specifies which tools it can use:

```yaml
# data-processor/SKILL.md
allowed-tools:
  - Read    # ✓ Can read files
  - Glob    # ✓ Can search for files
  - Bash    # ✓ Can run commands
  # ✗ Cannot Write (not in list)

# report-generator/SKILL.md
allowed-tools:
  - Write   # ✓ Can create files
  - Edit    # ✓ Can modify files
  - Read    # ✓ Can read files
  # ✗ Cannot run Bash (not in list)
```

**Why this matters:**
- Prevents data-processor from accidentally creating files
- Prevents report-generator from executing shell commands
- Provides clear security boundaries
- Enables safe skill composition

## 📁 Generated Files

After running `full_demo.py`:

```
examples/multi_skill_demo/demo_data/
├── sales_data.json      # Sample sales data
└── sales_report.md      # Generated analysis report
```

**sales_data.json** (sample):
```json
[
  {
    "date": "2024-01-15",
    "region": "North",
    "product": "Widget A",
    "amount": 1200
  },
  ...
]
```

**sales_report.md** (excerpt):
```markdown
# Sales Analysis Report

**Generated:** 2024-01-26
**Data Period:** 2024-01-15 to 2024-03-15

## Executive Summary
This report presents an analysis of Q1 2024 sales data...

## Key Findings
- **Total Sales:** $8400
- **Average Sale:** $1400
- **Top Product:** Widget A
```

## 🎓 Key Concepts Demonstrated

1. **Skill Modularity** - Skills are independent, reusable components
2. **Dynamic Selection** - Agent chooses skills based on task requirements
3. **Progressive Disclosure** - Load metadata fast, full content on demand
4. **Tool Restrictions** - Security through allowed-tools enforcement
5. **Multi-Skill Orchestration** - Complex workflows using multiple skills
6. **Sequential Execution** - Skills execute in order, passing data

## 🔧 What Was Fixed

During development, several issues were identified and fixed:

1. ✅ **Parameter Names** - `storage_config` → `config` for SkillLoader
2. ✅ **Index Building** - Added `loader.build_index()` call
3. ✅ **Attribute Access** - Fixed accessing SkillIndexEntry attributes
4. ✅ **SkillTool Parameter** - Changed to `skill_loader=loader`
5. ✅ **Skills Location** - Moved to `src/omniforge/skills/`

See `SUMMARY.md` for detailed technical fixes.

## 📚 Learn More

- **README.md** - Architecture and detailed examples
- **SUMMARY.md** - Technical details and fixes
- **Codebase** - `src/omniforge/skills/` for skills system
- **Tests** - `tests/builder/conversation/test_multi_skill.py`

## 🎉 Success Indicators

If everything works, you should see:

✅ Skills discovered and indexed
✅ Skills loaded with full content
✅ Tool restrictions displayed
✅ Multi-skill workflow executed
✅ Sample data and reports generated
✅ No errors in demo output

## 🚀 Next Steps

To extend this for production:

1. Replace keyword matching with LLM-based skill selection
2. Integrate with ToolExecutor for real tool execution
3. Add error handling and retry logic
4. Implement parallel skill execution
5. Add skill output chaining
6. Create more specialized skills
7. Add monitoring and observability

---

**Ready to try it?** Run the simple demo first:
```bash
python examples/multi_skill_demo/analyst_agent_simple.py
```

Enjoy exploring multi-skill agents! 🎊
