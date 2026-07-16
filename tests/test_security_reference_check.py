import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "security_reference_check.py"

spec = importlib.util.spec_from_file_location("security_reference_check", SCRIPT)
checker = importlib.util.module_from_spec(spec)
sys.modules["security_reference_check"] = checker
assert spec.loader is not None
spec.loader.exec_module(checker)


class SecurityReferenceTests(unittest.TestCase):
    def test_extracts_only_commit_pinned_github_file_references(self) -> None:
        commit = "a" * 40
        text = (
            f"https://github.com/rblake2320/example/blob/{commit}/SECURITY.md\n"
            "https://github.com/rblake2320/example/blob/master/SECURITY.md\n"
        )
        references = checker.extract_references(text)
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0].commit, commit)
        self.assertEqual(references[0].path, "SECURITY.md")

    def test_api_url_binds_path_to_exact_commit(self) -> None:
        commit = "b" * 40
        reference = checker.SecurityReference(
            owner="rblake2320",
            repo="example",
            commit=commit,
            path="docs/security policy.md",
            url="https://example.invalid",
        )
        self.assertEqual(
            reference.api_url,
            "https://api.github.com/repos/rblake2320/example/contents/"
            f"docs/security%20policy.md?ref={commit}",
        )

    def test_policy_contains_multiple_commit_pinned_component_policies(self) -> None:
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        references = checker.extract_references(text)
        self.assertGreaterEqual(len(references), 3)
        self.assertTrue(all(reference.path == "SECURITY.md" for reference in references))


if __name__ == "__main__":
    unittest.main()
