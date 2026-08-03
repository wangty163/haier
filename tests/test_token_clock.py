import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT_SOURCE = ROOT / "custom_components" / "haier" / "__init__.py"


class TokenClockTests(unittest.TestCase):
    def test_token_updater_uses_collision_safe_epoch_alias(self):
        source = INIT_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_aliases = {
            alias.asname
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "time"
            for alias in node.names
            if alias.name == "time"
        }
        self.assertIn("epoch_time", imported_aliases)
        direct_time_imports = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("time", direct_time_imports)
        self.assertGreaterEqual(source.count("epoch_time()"), 2)

        sibling_platform = ROOT / "custom_components" / "haier" / "time.py"
        self.assertTrue(sibling_platform.is_file())


if __name__ == "__main__":
    unittest.main()
