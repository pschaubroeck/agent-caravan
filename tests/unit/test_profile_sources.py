import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agentcaravan.profile import (
    ProfileError,
    find_organization_catalogs,
    load_configured_source,
    load_profile,
    resolve_source_path,
)


class ProfileSourceTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def _artifact(self, artifact_id: str, artifact_type: str = "role") -> dict:
        return {"artifact_type": artifact_type, "id": artifact_id}

    def test_legacy_absolute_and_profile_relative_paths_remain_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profile"
            source = profile / "sources"
            source.mkdir(parents=True)
            (source / "artifact.json").write_text(
                json.dumps(self._artifact("relative-role")), encoding="utf-8"
            )
            absolute_source = Path(temporary) / "absolute.json"
            absolute_source.write_text(
                json.dumps(self._artifact("absolute-role")), encoding="utf-8"
            )
            (profile / "config.json").write_text(json.dumps({
                "sources": ["sources", str(absolute_source)],
            }), encoding="utf-8")

            loaded = load_profile(profile)

            self.assertEqual({item["id"] for item in loaded["artifacts"]}, {
                "relative-role", "absolute-role",
            })
            self.assertEqual(loaded["source_provenance"], [])

    def test_git_source_reads_current_checkout_subdirectory_and_reports_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "shared-team"
            catalog = checkout / "catalog"
            catalog.mkdir(parents=True)
            self._git(checkout, "init", "-q")
            self._git(checkout, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                      "commit", "--allow-empty", "-m", "initial")
            artifact_path = catalog / "role.json"
            artifact_path.write_text(json.dumps(self._artifact("from-git")), encoding="utf-8")

            profile = root / "profile"
            profile.mkdir()
            (profile / "config.json").write_text(json.dumps({
                "sources": [{
                    "type": "git",
                    "url": "git@gitlab.example.test:teams/shared-team.git",
                    "checkout": "../shared-team",
                    "subdirectory": "catalog",
                }],
            }), encoding="utf-8")

            loaded = load_profile(profile)

            self.assertEqual([item["id"] for item in loaded["artifacts"]], ["from-git"])
            self.assertEqual(len(loaded["source_provenance"]), 1)
            provenance = loaded["source_provenance"][0]
            self.assertEqual(provenance["type"], "git")
            self.assertEqual(provenance["url"], "git@gitlab.example.test:teams/shared-team.git")
            self.assertEqual(provenance["checkout"], str(checkout.resolve()))
            self.assertEqual(provenance["subdirectory"], "catalog")
            self.assertEqual(provenance["revision"], self._git(checkout, "rev-parse", "HEAD"))
            self.assertTrue(provenance["dirty"])

            resolved_path = resolve_source_path(profile, json.loads(
                (profile / "config.json").read_text(encoding="utf-8")
            )["sources"][0])
            self.assertEqual(resolved_path, catalog.resolve())
            source_artifacts, source_provenance = load_configured_source(
                profile,
                json.loads((profile / "config.json").read_text(encoding="utf-8"))["sources"][0],
            )
            self.assertEqual(source_artifacts, loaded["artifacts"])
            self.assertEqual(source_provenance, provenance)

            catalogs = find_organization_catalogs(profile)
            self.assertEqual(catalogs, [])

    def test_git_source_can_discover_catalog_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "team"
            artifacts = checkout / "artifacts"
            artifacts.mkdir(parents=True)
            self._git(checkout, "init", "-q")
            self._git(checkout, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                      "commit", "--allow-empty", "-m", "initial")
            catalog = {
                "artifact_type": "organization-catalog",
                "id": "sample-org",
            }
            source_file = artifacts / "catalog.json"
            source_file.write_text(json.dumps(catalog), encoding="utf-8")
            profile = root / "profile"
            profile.mkdir()
            (profile / "config.json").write_text(json.dumps({
                "sources": [{"type": "git", "checkout": "../team", "subdirectory": "artifacts"}],
            }), encoding="utf-8")

            found = find_organization_catalogs(profile)

            self.assertEqual(found, [(catalog, source_file.resolve())])

    def test_git_source_requires_existing_local_checkout_and_never_fetches_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / "config.json").write_text(json.dumps({
                "sources": [{
                    "type": "git",
                    "url": "https://unreachable.example.invalid/org/team.git",
                    "checkout": "missing-checkout",
                }],
            }), encoding="utf-8")

            with self.assertRaisesRegex(ProfileError, "checkout does not exist"):
                load_profile(profile)

    def test_git_source_rejects_subdirectory_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "team"
            checkout.mkdir()
            self._git(checkout, "init", "-q")
            profile = root / "profile"
            profile.mkdir()
            (profile / "config.json").write_text(json.dumps({
                "sources": [{"type": "git", "checkout": "../team", "subdirectory": "../outside"}],
            }), encoding="utf-8")

            with self.assertRaisesRegex(ProfileError, "must stay inside"):
                load_profile(profile)

    def test_find_catalogs_validates_optional_git_source_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            for field, value, message in (
                ("url", 42, "url must be a non-empty string"),
                ("subdirectory", [], "subdirectory must be a non-empty string"),
            ):
                with self.subTest(field=field):
                    source = {"type": "git", "checkout": "checkout", field: value}
                    (profile / "config.json").write_text(json.dumps({"sources": [source]}), encoding="utf-8")
                    with self.assertRaisesRegex(ProfileError, message):
                        find_organization_catalogs(profile)


if __name__ == "__main__":
    unittest.main()
