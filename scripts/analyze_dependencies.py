"""Analyze module dependencies for complexity and optimization opportunities.

This script:
1. Maps all imports in the codebase
2. Identifies circular dependencies
3. Finds modules with too many dependencies
4. Detects unnecessary imports
5. Suggests optimizations
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DependencyAnalyzer:
    """Analyze Python module dependencies."""

    def __init__(self, root_dir: str):
        """Initialize analyzer with root directory."""
        self.root_dir = Path(root_dir)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.import_counts: Dict[str, int] = defaultdict(int)
        self.module_files: Dict[str, Path] = {}

    def analyze(self) -> None:
        """Analyze all Python files in the directory."""
        # Find all Python files
        for py_file in self.root_dir.rglob("*.py"):
            if "/__pycache__/" in str(py_file) or "/tests/" in str(py_file):
                continue

            module_name = self._get_module_name(py_file)
            self.module_files[module_name] = py_file

            # Parse imports
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(py_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._add_dependency(module_name, alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._add_dependency(module_name, node.module)
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")

    def _get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        rel_path = file_path.relative_to(self.root_dir)
        parts = list(rel_path.parts)

        # Remove .py extension
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # Remove __init__
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts)

    def _add_dependency(self, from_module: str, to_module: str) -> None:
        """Add a dependency relationship."""
        # Only track internal dependencies (omniforge.*)
        if to_module.startswith("omniforge"):
            self.dependencies[from_module].add(to_module)
            self.import_counts[to_module] += 1

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependency chains."""
        cycles = []
        visited = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in cycles and list(reversed(cycle)) not in cycles:
                    cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            for dep in self.dependencies.get(node, []):
                dfs(dep, path.copy())

        for module in self.dependencies:
            dfs(module, [])

        return cycles

    def find_heavy_modules(self, threshold: int = 10) -> List[Tuple[str, int]]:
        """Find modules with too many dependencies."""
        heavy = []
        for module, deps in self.dependencies.items():
            if len(deps) >= threshold:
                heavy.append((module, len(deps)))
        return sorted(heavy, key=lambda x: x[1], reverse=True)

    def find_unused_imports(self) -> Dict[str, List[str]]:
        """Find modules that are never imported (potential dead code)."""
        unused = {}
        all_modules = set(self.module_files.keys())
        imported_modules = set()

        for deps in self.dependencies.values():
            imported_modules.update(deps)

        for module in all_modules:
            if module not in imported_modules and not module.endswith("__init__"):
                # Check if it's a leaf module (not imported anywhere)
                unused[module] = []

        return unused

    def get_dependency_depth(self) -> Dict[str, int]:
        """Calculate dependency depth for each module."""
        depths = {}

        def calculate_depth(module: str, visited: Set[str]) -> int:
            if module in depths:
                return depths[module]

            if module in visited:
                return 0  # Circular dependency

            visited.add(module)
            deps = self.dependencies.get(module, set())

            if not deps:
                depths[module] = 0
                return 0

            max_depth = max(
                (calculate_depth(dep, visited.copy()) for dep in deps), default=0
            )
            depths[module] = max_depth + 1
            return depths[module]

        for module in self.dependencies:
            calculate_depth(module, set())

        return depths

    def report(self) -> None:
        """Generate a comprehensive dependency report."""
        print("=" * 80)
        print("DEPENDENCY ANALYSIS REPORT")
        print("=" * 80)

        # 1. Circular dependencies
        print("\n1. CIRCULAR DEPENDENCIES")
        print("-" * 80)
        cycles = self.find_circular_dependencies()
        if cycles:
            print(f"⚠️  Found {len(cycles)} circular dependency chain(s):")
            for i, cycle in enumerate(cycles, 1):
                print(f"\n  Cycle {i}:")
                for j, module in enumerate(cycle):
                    if j < len(cycle) - 1:
                        print(f"    {module}")
                        print(f"      ↓ imports")
                    else:
                        print(f"    {module}")
        else:
            print("✅ No circular dependencies found!")

        # 2. Heavy modules
        print("\n\n2. MODULES WITH MANY DEPENDENCIES (>10)")
        print("-" * 80)
        heavy = self.find_heavy_modules(threshold=10)
        if heavy:
            print(f"⚠️  Found {len(heavy)} module(s) with high dependency counts:\n")
            for module, count in heavy[:10]:  # Top 10
                print(f"  {module}: {count} dependencies")
                if count > 20:
                    print(f"    ❌ CRITICAL: Consider breaking down this module")
                elif count > 15:
                    print(f"    ⚠️  WARNING: High complexity")
        else:
            print("✅ All modules have reasonable dependency counts!")

        # 3. Most imported modules
        print("\n\n3. MOST IMPORTED MODULES (Coupling Analysis)")
        print("-" * 80)
        top_imported = sorted(
            self.import_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        print("Top 10 most imported modules:\n")
        for module, count in top_imported:
            status = "✅" if count < 10 else "⚠️" if count < 20 else "❌"
            print(f"  {status} {module}: imported {count} times")

        # 4. Dependency depth
        print("\n\n4. DEPENDENCY DEPTH (Chain Length)")
        print("-" * 80)
        depths = self.get_dependency_depth()
        deep_modules = sorted(depths.items(), key=lambda x: x[1], reverse=True)[:10]
        print("Top 10 deepest dependency chains:\n")
        for module, depth in deep_modules:
            status = "✅" if depth < 5 else "⚠️" if depth < 8 else "❌"
            print(f"  {status} {module}: depth {depth}")

        # 5. Potentially unused modules
        print("\n\n5. POTENTIALLY UNUSED MODULES")
        print("-" * 80)
        unused = self.find_unused_imports()
        if unused:
            print(f"⚠️  Found {len(unused)} module(s) never imported:\n")
            for module in list(unused.keys())[:10]:
                print(f"  - {module}")
                print(f"    💡 Check if this is dead code")
        else:
            print("✅ All modules are imported somewhere!")

        # 6. Recommendations
        print("\n\n6. OPTIMIZATION RECOMMENDATIONS")
        print("-" * 80)

        recommendations = []

        # Check for circular dependencies
        if cycles:
            recommendations.append(
                "❌ CRITICAL: Fix circular dependencies by:\n"
                "   - Using TYPE_CHECKING imports\n"
                "   - Moving shared code to a separate module\n"
                "   - Using dependency injection"
            )

        # Check for heavy modules
        if len(heavy) > 0 and heavy[0][1] > 20:
            recommendations.append(
                f"⚠️  Module '{heavy[0][0]}' has {heavy[0][1]} dependencies.\n"
                "   Consider splitting into smaller, focused modules."
            )

        # Check coupling
        if top_imported and top_imported[0][1] > 20:
            recommendations.append(
                f"⚠️  '{top_imported[0][0]}' is imported {top_imported[0][1]} times.\n"
                "   High coupling - consider:\n"
                "   - Using interfaces/protocols\n"
                "   - Dependency injection\n"
                "   - Breaking into smaller modules"
            )

        # Check depth
        if deep_modules and deep_modules[0][1] > 8:
            recommendations.append(
                f"⚠️  Deep dependency chain (depth {deep_modules[0][1]}) in '{deep_modules[0][0]}'.\n"
                "   Consider flattening the hierarchy."
            )

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec}")
        else:
            print("✅ No critical issues found! Dependencies are well-structured.")

        print("\n" + "=" * 80)


def main() -> None:
    """Run dependency analysis."""
    root_dir = Path(__file__).parent.parent / "src" / "omniforge"

    print(f"Analyzing dependencies in: {root_dir}\n")

    analyzer = DependencyAnalyzer(str(root_dir))
    analyzer.analyze()
    analyzer.report()


if __name__ == "__main__":
    main()
