import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECURITY = ROOT / "SECURITY.md"


class SecurityPolicyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SECURITY.read_text(encoding="utf-8")

    def test_current_policy_does_not_use_unbounded_guarantee_heading(self) -> None:
        self.assertNotIn("## What This System Guarantees", self.text)
        self.assertNotIn("computationally impossible", self.text.lower())
        self.assertNotIn("0 breaches", self.text.lower())
        self.assertNotIn("post-quantum migration-ready", self.text.lower())

    def test_cross_repository_security_links_are_commit_pinned(self) -> None:
        self.assertNotRegex(self.text, r"/blob/(?:main|master)/SECURITY\.md")
        for repository, commit in (
            ("tsk-protocol", "abbcb210fe77fc9ec00763138caa007be57ef5d3"),
            ("bpc-protocol", "2a23fcfb5f17d95e84c4de21363fda9ca141a225"),
            (
                "selfconnect-enterprise",
                "57d020caf28a0489c08c2cfc316ab392cef1a62b",
            ),
        ):
            self.assertIn(
                f"https://github.com/rblake2320/{repository}/blob/{commit}/SECURITY.md",
                self.text,
            )
        self.assertNotIn("selfconnect/blob/", self.text)

    def test_component_policy_pins_match_current_gitlinks(self) -> None:
        for path in ("tsk", "bpc", "enterprise"):
            result = subprocess.run(
                ["git", "ls-files", "--stage", "--", path],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            fields = result.stdout.split()
            self.assertGreaterEqual(len(fields), 2)
            self.assertEqual(fields[0], "160000")
            self.assertIn(fields[1], self.text)

    def test_every_repo_local_evidence_path_exists(self) -> None:
        evidence_section = self.text.split("## Executable Evidence in This Repository", 1)[1]
        evidence_section = evidence_section.split("## Bounded Security Properties", 1)[0]
        paths = {
            token
            for token in re.findall(r"`([^`]+)`", evidence_section)
            if "/" in token and not token.startswith("http")
        }
        self.assertTrue(paths)
        missing = sorted(path for path in paths if not (ROOT / path).is_file())
        self.assertEqual(missing, [])

    def test_disclosure_channel_forbids_public_exploit_details(self) -> None:
        self.assertIn("## Reporting a Vulnerability", self.text)
        self.assertIn("Do not open a public issue", self.text)
        self.assertIn("Security** / **Advisories", self.text)
        self.assertIn("Private Vulnerability Reporting is not", self.text)
        self.assertIn("synthetic data", self.text)
        self.assertIn("not authorized", self.text)

    def test_authorization_and_test_boundaries_are_explicit(self) -> None:
        self.assertIn("do not prove the absence of vulnerabilities", self.text.lower())
        self.assertIn("Nothing in this repository grants or proves an ATO", self.text)
        self.assertIn("not a live-environment readiness result", self.text)
        self.assertIn("SECURITY-ANALYSIS.md", self.text)
        self.assertIn("does not trust an artifact manifest's `signed` field", self.text)


if __name__ == "__main__":
    unittest.main()
