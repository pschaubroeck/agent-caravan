import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan import managed_skills


class SkillInstallationTests(unittest.TestCase):
    def _install(self, source: Path, destination_root: Path, answers=()):
        answer_iterator = iter(answers)
        with patch.object(managed_skills, "skill_ids_for_runtime", return_value=("example-skill",)), patch.object(
            managed_skills, "packaged_skill_path", return_value=source
        ):
            managed_skills.install_skills(
                destination_root,
                confirm_replace=lambda _: next(answer_iterator).strip().casefold() in {"y", "yes"},
            )

    def test_unmanaged_skill_is_preserved_without_prompt(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("user-owned\n", encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "user-owned\n")
            self.assertFalse((destination / managed_skills.MANAGED_SKILL_MARKER).exists())

    def test_managed_skill_refreshes_when_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            marker = json.loads((destination / managed_skills.MANAGED_SKILL_MARKER).read_text(encoding="utf-8"))

            (source / "SKILL.md").write_text("updated package\n", encoding="utf-8")
            self._install(source, skills_root)

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "updated package\n")
            refreshed = json.loads((destination / managed_skills.MANAGED_SKILL_MARKER).read_text(encoding="utf-8"))
            self.assertNotEqual(marker["content_hash"], refreshed["content_hash"])

    def test_legacy_unchanged_skill_is_adopted(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("packaged\n", encoding="utf-8")

            self._install(source, root / "skills")

            self.assertTrue((destination / managed_skills.MANAGED_SKILL_MARKER).is_file())

    def test_legacy_modified_skill_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")
            self.assertFalse((destination / managed_skills.MANAGED_SKILL_MARKER).exists())

    def test_invalid_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("user-owned\n", encoding="utf-8")
            (destination / managed_skills.MANAGED_SKILL_MARKER).write_text(
                json.dumps({"managed_by": "agentcaravan"}), encoding="utf-8"
            )

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "user-owned\n")

    def test_malformed_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local\n", encoding="utf-8")
            (destination / managed_skills.MANAGED_SKILL_MARKER).write_text("{not-json", encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local\n")

    def test_wrong_package_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local\n", encoding="utf-8")
            marker = {
                "format_version": managed_skills.MANAGED_SKILL_FORMAT_VERSION,
                "managed_by": "agentcaravan",
                "artifact_type": "runtime-skill-installation",
                "skill_id": "example-skill",
                "package_name": "other-package",
                "content_hash": "0" * 64,
            }
            (destination / managed_skills.MANAGED_SKILL_MARKER).write_text(json.dumps(marker), encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local\n")

    def test_invalid_hash_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local\n", encoding="utf-8")
            marker = {
                "format_version": managed_skills.MANAGED_SKILL_FORMAT_VERSION,
                "managed_by": "agentcaravan",
                "artifact_type": "runtime-skill-installation",
                "skill_id": "example-skill",
                "package_name": "agent-caravan",
                "content_hash": "not-a-sha256",
            }
            (destination / managed_skills.MANAGED_SKILL_MARKER).write_text(json.dumps(marker), encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local\n")

    def test_symlinked_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local\n", encoding="utf-8")
            marker_target = root / "external-marker.json"
            marker_target.write_text("{}", encoding="utf-8")
            (destination / managed_skills.MANAGED_SKILL_MARKER).symlink_to(marker_target)

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local\n")

    def test_mismatched_marker_skill_id_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            marker = {
                "format_version": managed_skills.MANAGED_SKILL_FORMAT_VERSION,
                "managed_by": "agentcaravan",
                "artifact_type": "runtime-skill-installation",
                "skill_id": "other-skill",
                "package_name": "agent-caravan",
                "content_hash": "0" * 64,
            }
            (destination / managed_skills.MANAGED_SKILL_MARKER).write_text(json.dumps(marker), encoding="utf-8")

            self._install(source, root / "skills")

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_empty_directory_change_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "empty").mkdir()

            self._install(source, skills_root, answers=("n",))

            self.assertTrue((destination / "empty").is_dir())

    def test_copy_failure_preserves_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            with patch.object(managed_skills.shutil, "copytree", side_effect=OSError("copy failed")):
                with self.assertRaises(OSError):
                    self._install(source, skills_root, answers=("y",))

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_marker_write_failure_preserves_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            with patch.object(managed_skills, "_write_skill_marker", side_effect=OSError("marker failed")):
                with self.assertRaises(OSError):
                    self._install(source, skills_root, answers=("y",))

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_final_rename_failure_restores_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            original_rename = Path.rename

            def fail_staged_rename(path, target):
                if path.name == "replacement":
                    raise OSError("final rename failed")
                return original_rename(path, target)

            with patch.object(Path, "rename", autospec=True, side_effect=fail_staged_rename):
                with self.assertRaises(OSError):
                    self._install(source, skills_root, answers=("y",))

            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_added_file_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            skill = root / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("content\n", encoding="utf-8")
            original = managed_skills.skill_fingerprint(skill)
            (skill / "extra.txt").write_text("extra\n", encoding="utf-8")
            self.assertNotEqual(original, managed_skills.skill_fingerprint(skill))

    def test_removed_file_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            skill = root / "skill"
            skill.mkdir()
            file_path = skill / "SKILL.md"
            file_path.write_text("content\n", encoding="utf-8")
            original = managed_skills.skill_fingerprint(skill)
            file_path.unlink()
            self.assertNotEqual(original, managed_skills.skill_fingerprint(skill))

    def test_empty_directory_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            skill = root / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("content\n", encoding="utf-8")
            original = managed_skills.skill_fingerprint(skill)
            (skill / "empty").mkdir()
            self.assertNotEqual(original, managed_skills.skill_fingerprint(skill))

    def test_symlinked_skill_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            destination = root / "skills" / "example-skill"
            destination.mkdir(parents=True)
            target = root / "user-owned"
            target.mkdir()
            (target / "SKILL.md").write_text("user-owned\n", encoding="utf-8")
            destination.rmdir()
            destination.symlink_to(target, target_is_directory=True)

            self._install(source, root / "skills")

            self.assertTrue(destination.is_symlink())
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "user-owned\n")

    def test_modified_managed_skill_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            self._install(source, skills_root, answers=("n",))
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

            self._install(source, skills_root, answers=("y",))
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "packaged\n")

    def test_modified_managed_skill_accepts_uppercase_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("packaged\n", encoding="utf-8")
            skills_root = root / "skills"

            self._install(source, skills_root)
            destination = skills_root / "example-skill"
            (destination / "SKILL.md").write_text("local edit\n", encoding="utf-8")

            self._install(source, skills_root, answers=("Y",))
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "packaged\n")


if __name__ == "__main__":
    unittest.main()
