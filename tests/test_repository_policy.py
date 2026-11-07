"""Local regression guards for project identity and source-only publication."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryPolicyTests(unittest.TestCase):
    def test_canonical_identity_references(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        plugin = "Dock" if (ROOT / "Dock.qml").is_file() else "Launchpad"
        self.assertEqual(manifest["id"], "okuma.dev_" + plugin.lower() + "4omarchy")
        self.assertEqual(manifest["author"], "\u014cKUMA")
        self.assertIn("https://github.com/Okumai/" + plugin,
                      (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_no_github_actions_workflows(self):
        directory = ROOT / ".github/workflows"
        workflows = [path for path in directory.rglob("*")
                     if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}]
        self.assertEqual(workflows, [], "This project uses local tests, not GitHub Actions")


if __name__ == "__main__":
    unittest.main()
