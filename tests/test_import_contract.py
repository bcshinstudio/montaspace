"""Catch absent imports inside the application without requiring PySide6.

This is source-level validation; real runtime imports are still exercised by
mandatory Windows GUI regression tests.
"""
import ast
from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[1] / "app"


def exported_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            names.update(target.id for target in targets if isinstance(target, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


class InternalImportContractTests(unittest.TestCase):
    def test_relative_imports_resolve_to_existing_modules_and_names(self):
        trees = {p.stem: ast.parse(p.read_text(encoding="utf-8"))
                 for p in APP.glob("*.py")}
        exports = {module: exported_names(tree) for module, tree in trees.items()}
        errors = []
        for module, tree in trees.items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level != 1:
                    continue
                if not node.module:
                    continue
                if node.module not in exports:
                    errors.append(f"{module}: missing app.{node.module} module")
                    continue
                for name in node.names:
                    if name.name != "*" and name.name not in exports[node.module]:
                        errors.append(f"{module}: app.{node.module}.{name.name} not found")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
