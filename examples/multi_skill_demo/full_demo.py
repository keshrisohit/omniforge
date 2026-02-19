"""
Full Multi-Skill Agent Demo

This script demonstrates a complete end-to-end example of:
1. Creating sample data
2. Using an agent that dynamically selects skills
3. Processing data with the data-processor skill
4. Generating a report with the report-generator skill
5. Showing how SkillTool and ToolExecutor work together
"""

import os
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from omniforge.skills.loader import SkillLoader
from omniforge.skills.tool import SkillTool
from omniforge.skills.storage import StorageConfig
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


def setup_demo_environment():
    """Set up the demo environment with sample data."""
    print("🔧 Setting up demo environment...")

    # Create demo data directory
    demo_dir = Path(__file__).parent / "demo_data"
    demo_dir.mkdir(exist_ok=True)

    # Create sample sales data
    sales_data = [
        {"date": "2024-01-15", "region": "North", "product": "Widget A", "amount": 1200},
        {"date": "2024-01-20", "region": "South", "product": "Widget B", "amount": 850},
        {"date": "2024-02-05", "region": "North", "product": "Widget A", "amount": 1500},
        {"date": "2024-02-10", "region": "East", "product": "Widget C", "amount": 2100},
        {"date": "2024-03-01", "region": "South", "product": "Widget B", "amount": 950},
        {"date": "2024-03-15", "region": "West", "product": "Widget A", "amount": 1800},
    ]

    sales_file = demo_dir / "sales_data.json"
    with open(sales_file, "w") as f:
        json.dump(sales_data, f, indent=2)

    print(f"✓ Created sample data: {sales_file}")
    return demo_dir


def demonstrate_skill_discovery():
    """Demonstrate skill discovery and listing."""
    print("\n" + "=" * 80)
    print("STEP 1: SKILL DISCOVERY")
    print("=" * 80)

    # Initialize skill loader
    # Point to skills in src/omniforge/skills
    project_root = Path(__file__).parent.parent.parent
    skills_path = project_root / "src" / "omniforge" / "skills"

    # Use plugin_paths to include our custom skills location
    storage_config = StorageConfig(plugin_paths=[skills_path])

    loader = SkillLoader(config=storage_config)

    # Build the index to discover skills
    skill_count = loader.build_index()
    print(f"\n📦 Indexed {skill_count} skills from {skills_path}")

    print("\n📚 Available skills in the system:")
    skills = loader.list_skills()

    for skill in skills:
        print(f"\n  • {skill.name}")
        print(f"    Description: {skill.description}")
        if skill.tags:
            print(f"    Tags: {', '.join(skill.tags)}")
        print(f"    Priority: {skill.priority}")
        print(f"    Storage Layer: {skill.storage_layer}")

    return loader


def demonstrate_multi_skill_workflow(loader: SkillLoader, demo_dir: Path):
    """Demonstrate using multiple skills to complete a task."""
    print("\n" + "=" * 80)
    print("STEP 2: MULTI-SKILL WORKFLOW")
    print("=" * 80)

    task = "Analyze the sales data and generate a comprehensive report"
    print(f"\n🎯 Task: {task}")

    # Simulate agent decision-making
    print("\n🤖 Agent reasoning:")
    print("  1. This task requires data analysis → use 'data-processor' skill")
    print("  2. This task requires report generation → use 'report-generator' skill")
    print("  3. These skills should be used sequentially")

    # Part 1: Use data-processor skill
    print("\n" + "-" * 80)
    print("EXECUTING: data-processor skill")
    print("-" * 80)

    # Load the data-processor skill
    data_processor_skill = loader.load_skill("data-processor")

    if data_processor_skill:
        print(f"\n✓ Loaded skill: {data_processor_skill.metadata.name}")
        print(f"  Description: {data_processor_skill.metadata.description}")
        print(f"  Allowed tools: {data_processor_skill.metadata.allowed_tools}")

        print("\n📝 Skill instructions (first 500 chars):")
        print(data_processor_skill.content[:500] + "...")

        print("\n🔧 In a real implementation, the agent would:")
        print("  • Use Read tool to load sales_data.json")
        print("  • Parse and analyze the data")
        print("  • Calculate key metrics (total sales, avg by region, etc.)")
        print("  • Return structured analysis results")

        # Simulate the analysis results
        analysis_results = {
            "total_sales": 8400,
            "avg_sale": 1400,
            "regions": ["North", "South", "East", "West"],
            "top_product": "Widget A",
            "date_range": "2024-01-15 to 2024-03-15",
        }

        print(f"\n📊 Analysis Results:")
        for key, value in analysis_results.items():
            print(f"  • {key}: {value}")
    else:
        print("❌ Failed to load data-processor skill")
        return

    # Part 2: Use report-generator skill
    print("\n" + "-" * 80)
    print("EXECUTING: report-generator skill")
    print("-" * 80)

    # Load the report-generator skill
    report_generator_skill = loader.load_skill("report-generator")

    if report_generator_skill:
        print(f"\n✓ Loaded skill: {report_generator_skill.metadata.name}")
        print(f"  Description: {report_generator_skill.metadata.description}")
        print(f"  Allowed tools: {report_generator_skill.metadata.allowed_tools}")

        print("\n📝 Skill instructions (first 500 chars):")
        print(report_generator_skill.content[:500] + "...")

        print("\n🔧 In a real implementation, the agent would:")
        print("  • Take analysis results from previous step")
        print("  • Format data into professional report structure")
        print("  • Use Write tool to create sales_report.md")
        print("  • Include executive summary, findings, recommendations")

        # Simulate creating a report
        report_file = demo_dir / "sales_report.md"
        report_content = f"""# Sales Analysis Report

**Generated:** 2024-01-26
**Data Period:** {analysis_results['date_range']}

## Executive Summary

This report presents an analysis of Q1 2024 sales data across four regions.
Total sales reached ${analysis_results['total_sales']} with an average transaction
value of ${analysis_results['avg_sale']}.

## Key Findings

- **Total Sales:** ${analysis_results['total_sales']}
- **Average Sale:** ${analysis_results['avg_sale']}
- **Top Product:** {analysis_results['top_product']}
- **Active Regions:** {', '.join(analysis_results['regions'])}

## Recommendations

1. Increase inventory for {analysis_results['top_product']}
2. Expand marketing efforts in underperforming regions
3. Analyze seasonal trends for better forecasting

## Conclusion

Strong performance in Q1 with clear opportunities for growth in Q2.
"""

        with open(report_file, "w") as f:
            f.write(report_content)

        print(f"\n✓ Report generated: {report_file}")
        print(f"\n📄 Report preview:")
        print("-" * 40)
        print(report_content[:400] + "...")
        print("-" * 40)
    else:
        print("❌ Failed to load report-generator skill")
        return

    print("\n✅ Multi-skill workflow completed successfully!")
    print(f"\n💾 Output files:")
    print(f"  • Data: {demo_dir / 'sales_data.json'}")
    print(f"  • Report: {demo_dir / 'sales_report.md'}")


def demonstrate_tool_restrictions():
    """Demonstrate how skills restrict which tools can be used."""
    print("\n" + "=" * 80)
    print("STEP 3: TOOL RESTRICTIONS")
    print("=" * 80)

    print("\n🔒 How tool restrictions work:")
    print("\n  data-processor skill allows: Read, Glob, Bash")
    print("    ✓ Can read files and search for data")
    print("    ✗ Cannot write files (enforced by ToolExecutor)")

    print("\n  report-generator skill allows: Write, Edit, Read")
    print("    ✓ Can create and modify report files")
    print("    ✗ Cannot execute shell commands (enforced by ToolExecutor)")

    print("\n💡 Benefits:")
    print("  • Security: Prevents skills from doing unintended actions")
    print("  • Clarity: Makes skill capabilities explicit")
    print("  • Composability: Skills can be safely combined")


def demonstrate_skill_tool_integration():
    """Demonstrate how SkillTool provides progressive disclosure."""
    print("\n" + "=" * 80)
    print("STEP 4: SKILL TOOL INTEGRATION")
    print("=" * 80)

    project_root = Path(__file__).parent.parent.parent
    skills_path = project_root / "src" / "omniforge" / "skills"
    storage_config = StorageConfig(plugin_paths=[skills_path])

    # Create loader and build index
    loader = SkillLoader(config=storage_config)
    loader.build_index()

    print("\n📦 SkillTool provides progressive disclosure:")
    print("\n  Stage 1: List available skills (lightweight)")
    skill_tool = SkillTool(skill_loader=loader)

    # Get the tool definition which includes skill descriptions
    tool_def = skill_tool.definition
    print(f"  Tool name: {tool_def.name}")
    print(f"  Tool description (first 300 chars): {tool_def.description[:300]}...")

    print("\n  Stage 2: Load full skill on demand (with restrictions)")
    print("  • Full skill content + instructions")
    print("  • Allowed tools enforcement")
    print("  • Base path for file references")


def main():
    """Run the complete multi-skill demo."""
    print("\n" + "=" * 80)
    print("OMNIFORGE - MULTI-SKILL AGENT DEMONSTRATION")
    print("=" * 80)

    try:
        # Setup
        demo_dir = setup_demo_environment()

        # Demonstrate skill discovery
        loader = demonstrate_skill_discovery()

        # Demonstrate multi-skill workflow
        demonstrate_multi_skill_workflow(loader, demo_dir)

        # Demonstrate tool restrictions
        demonstrate_tool_restrictions()

        # Demonstrate SkillTool integration
        demonstrate_skill_tool_integration()

        print("\n" + "=" * 80)
        print("✅ DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)

        print("\n📚 Summary:")
        print("  • Created 2 skills: data-processor, report-generator")
        print("  • Demonstrated skill discovery and loading")
        print("  • Showed multi-skill orchestration workflow")
        print("  • Explained tool restrictions for security")
        print("  • Illustrated SkillTool progressive disclosure")

        print("\n🎯 Key Takeaways:")
        print("  1. Skills are modular and composable")
        print("  2. Agents can dynamically select which skills to use")
        print("  3. Tool restrictions provide security boundaries")
        print("  4. Multi-skill workflows enable complex tasks")
        print("  5. Progressive disclosure keeps context efficient")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
