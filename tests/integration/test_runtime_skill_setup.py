import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan import cli, managed_skills
from agentcaravan.resolve_framework import resolve_profile
from tools.init_agentcaravan import main as checkout_init


class RuntimeSkillSetupTests(unittest.TestCase):
    def _snapshot_tree(self, root):
        if not root.exists():
            return None
        snapshot = {".": "directory"}
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            snapshot[relative] = "directory" if path.is_dir() else path.read_bytes()
        return snapshot

    def _init(self, root, runtime=None, skill_root=None, team="Platform Team"):
        args = ["init", "--root", str(root), "--organization", "Example Organization", "--team", team]
        if runtime:
            args.extend(["--runtime", runtime])
        if skill_root:
            args.extend(["--skill-root", str(skill_root)])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(args), 0)

    def test_default_codex_and_explicit_runtime_install_selected_skills_and_resolve(self):
        for runtime, adapter, profile, destination in (
            (None, "codex-desktop-agent-runtime", "codex-desktop-information-technology-core-team", ".agents/skills"),
            ("opencode", "opencode-agent-runtime", "opencode-information-technology-core-team", ".config/opencode/skills"),
            ("kiro", "kiro-ide-agent-runtime", "kiro-ide-information-technology-core-team", ".kiro/skills"),
        ):
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                root = home / "profile"
                with patch.object(Path, "home", return_value=home):
                    self._init(root, runtime)
                    resolved = resolve_profile(root)
                    report = cli._status_report(root)
                selected = runtime or "codex"
                self.assertEqual(resolved["status"], "degraded" if selected in {"opencode", "kiro"} else "pass")
                self.assertEqual(resolved["context"]["runtime_adapter_id"], adapter)
                self.assertEqual(resolved["context"]["runtime_profile_id"], profile)
                self.assertEqual(report["skills"]["status"], "installed")
                self.assertEqual(report["skills"]["runtime"], selected)
                self.assertEqual(report["skills"]["root"], str(home / destination))
                self.assertEqual(
                    {path.name for path in (home / destination).iterdir()},
                    set(managed_skills.skill_ids_for_runtime(selected)),
                )

    def test_refresh_keeps_custom_root_and_preserves_modified_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "custom-skills"
            self._init(root, "opencode", skills)
            skill = skills / "agent-caravan-builder" / "SKILL.md"
            skill.write_text("local customization\n", encoding="utf-8")
            with patch("builtins.input", return_value="n"):
                self._init(root, "opencode")
            self.assertEqual(skill.read_text(encoding="utf-8"), "local customization\n")
            report = cli._status_report(root)
            self.assertEqual(report["skills"]["root"], str(skills))
            self.assertEqual(report["skills"]["status"], "modified")
            self.assertIn("agent-caravan-builder", report["skills"]["modified"])

    def test_legacy_codex_custom_root_is_preserved_on_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "legacy-skills"
            self._init(root, skill_root=skills)
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config.pop("managed_skill_roots")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            self.assertEqual(cli._status_report(root)["skills"]["root"], str(skills))
            self._init(root)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["managed_skill_roots"]["codex"], str(skills))

    def test_status_uses_team_runtime_when_legacy_context_omits_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, skill_root=skills)
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"].pop("runtime_adapter_id")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            self.assertEqual(cli._status_report(root)["skills"]["status"], "installed")
            self.assertEqual(cli._status_report(root)["skills"]["root"], str(skills))

    def test_opencode_strict_policy_rejects_empty_bootstrap_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            cli.bootstrap(root)
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"]["validation_profile_id"] = "organization-shared"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            skills = Path(directory) / "skills"
            skills.mkdir()
            profile_before = self._snapshot_tree(root)
            skills_before = self._snapshot_tree(skills)
            with self.assertRaisesRegex(SystemExit, "validation profile|degraded runtime capabilities"), contextlib.redirect_stdout(io.StringIO()):
                cli.main([
                    "init", "--root", str(root), "--organization", "Example Organization",
                    "--team", "OpenCode Team", "--runtime", "opencode", "--skill-root", str(skills),
                ])
            self.assertEqual(self._snapshot_tree(root), profile_before)
            self.assertEqual(self._snapshot_tree(skills), skills_before)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["active_context"]["validation_profile_id"], "organization-shared")

    def test_opencode_strict_policy_rejects_new_team_without_changing_working_codex_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "codex-skills"
            self._init(root, skill_root=skills, team="Codex Team")
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"]["validation_profile_id"] = "organization-shared"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            self.assertEqual(resolve_profile(root)["status"], "pass")
            profile_before = self._snapshot_tree(root)
            skills_before = self._snapshot_tree(skills)
            opencode_skills = Path(directory) / "opencode-skills"

            with self.assertRaisesRegex(SystemExit, "validation profile|degraded runtime capabilities"), contextlib.redirect_stdout(io.StringIO()):
                cli.main([
                    "init", "--root", str(root), "--organization", "Example Organization",
                    "--team", "OpenCode Team", "--runtime", "opencode",
                    "--skill-root", str(opencode_skills),
                ])

            self.assertEqual(self._snapshot_tree(root), profile_before)
            self.assertEqual(self._snapshot_tree(skills), skills_before)
            self.assertIsNone(self._snapshot_tree(opencode_skills))
            resolved = resolve_profile(root)
            self.assertEqual(resolved["status"], "pass")
            self.assertEqual(resolved["context"]["runtime_adapter_id"], "codex-desktop-agent-runtime")
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["active_context"]["validation_profile_id"], "organization-shared")

    def test_checkout_strict_policy_rejection_preserves_legacy_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, "opencode", skills)
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"]["validation_profile_id"] = "organization-shared"
            legacy_source = "/old/checkout/resources/core/agentcaravan-core-team.json"
            config["sources"].append(legacy_source)
            config_path.write_text(json.dumps(config), encoding="utf-8")
            profile_before = self._snapshot_tree(root)
            skills_before = self._snapshot_tree(skills)

            with patch.object(sys, "argv", [
                "init_agentcaravan.py", "--root", str(root), "--runtime", "opencode", "--skill-root", str(skills),
            ]), patch("builtins.input", side_effect=["1", "", ""]), self.assertRaisesRegex(
                SystemExit, "validation profile|degraded runtime capabilities"
            ), contextlib.redirect_stdout(io.StringIO()):
                checkout_init()

            self.assertEqual(self._snapshot_tree(root), profile_before)
            self.assertEqual(self._snapshot_tree(skills), skills_before)
            after = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn(legacy_source, after["sources"])
            self.assertEqual(after["active_context"]["validation_profile_id"], "organization-shared")

    def test_opencode_strict_policy_rejection_preserves_modified_custom_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "custom-skills"
            self._init(root, "opencode", skills)
            customized = skills / "agent-caravan-builder" / "SKILL.md"
            customized.write_text("local customization\n", encoding="utf-8")
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"]["validation_profile_id"] = "organization-shared"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            profile_before = self._snapshot_tree(root)
            skills_before = self._snapshot_tree(skills)

            with self.assertRaisesRegex(SystemExit, "validation profile|degraded runtime capabilities"), contextlib.redirect_stdout(io.StringIO()):
                cli.main([
                    "init", "--root", str(root), "--runtime", "opencode", "--skill-root", str(skills),
                    "--organization", "Example Organization", "--team", "OpenCode Team",
                ])

            self.assertEqual(self._snapshot_tree(root), profile_before)
            self.assertEqual(self._snapshot_tree(skills), skills_before)
            self.assertEqual(customized.read_text(encoding="utf-8"), "local customization\n")

    def test_checkout_mismatch_preserves_legacy_source_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            self._init(root, "opencode", Path(directory) / "skills")
            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["sources"].append("/old/checkout/resources/core/agentcaravan-core-team.json")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            before = config_path.read_bytes()
            with patch.object(sys, "argv", ["init_agentcaravan.py", "--root", str(root)]), patch(
                "builtins.input", side_effect=["1", ""]
            ), self.assertRaisesRegex(SystemExit, "uses opencode, not codex"), contextlib.redirect_stdout(io.StringIO()):
                checkout_init()
            self.assertEqual(config_path.read_bytes(), before)

    def test_coexisting_runtimes_keep_separate_roots_and_can_share_one_skill_root(self):
        for shared in (False, True):
            with self.subTest(shared=shared), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "profile"
                codex_root = Path(directory) / "codex-skills"
                opencode_root = codex_root if shared else Path(directory) / "opencode-skills"
                self._init(root, "codex", codex_root, "Codex Team")
                self._init(root, "opencode", opencode_root, "OpenCode Team")
                config = json.loads((root / "config.json").read_text(encoding="utf-8"))
                self.assertEqual(config["managed_skill_roots"], {"codex": str(codex_root), "opencode": str(opencode_root)})
                self.assertEqual(cli._status_report(root)["skills"]["root"], str(opencode_root))
                self._init(root, "codex", team="Codex Team")
                self.assertEqual(cli._status_report(root)["skills"]["root"], str(codex_root))
                self.assertTrue((codex_root / "agent-caravan-codex-orchestrator").is_dir())
                self.assertTrue((opencode_root / "agent-caravan-opencode-orchestrator").is_dir())

    def test_runtime_mismatch_fails_before_modifying_existing_profile_or_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, "opencode", skills)
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            other_skills = Path(directory) / "other-skills"
            with self.assertRaisesRegex(SystemExit, "uses opencode, not codex"), contextlib.redirect_stdout(io.StringIO()):
                cli.main(["init", "--root", str(root), "--skill-root", str(other_skills)])
            after = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(after, before)
            self.assertFalse(other_skills.exists())

    def test_non_active_organization_conflict_is_rejected_before_selection_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, skill_root=skills, team="Active Team")
            with contextlib.redirect_stdout(io.StringIO()):
                cli.main([
                    "init", "--root", str(root), "--organization", "Other Organization",
                    "--team", "Selected Team", "--skill-root", str(skills),
                ])
            self._init(root, team="Active Team")
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            other_skills = Path(directory) / "opencode-skills"
            with patch("builtins.input") as prompt, self.assertRaisesRegex(SystemExit, "uses codex, not opencode"):
                cli.main([
                    "init", "--root", str(root), "--runtime", "opencode",
                    "--team", "Selected Team", "--skill-root", str(other_skills),
                ])
            prompt.assert_not_called()
            after = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(other_skills.exists())

    def test_runtime_neutral_existing_team_is_bound_in_context_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, skill_root=skills)
            team_path = root / "sources/example-organization/example-organization-platform-team.json"
            team = json.loads(team_path.read_text(encoding="utf-8"))
            team["runtime_defaults"] = []
            team_path.write_text(json.dumps(team), encoding="utf-8")
            before = team_path.read_bytes()
            self._init(root, "opencode", skills)
            self.assertEqual(team_path.read_bytes(), before)
            self.assertEqual(resolve_profile(root)["context"]["runtime_adapter_id"], "opencode-agent-runtime")

    def test_refresh_reuses_active_team_without_organization_overwrite_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            self._init(root, "opencode", skills)
            with patch("builtins.input") as prompt, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["init", "--root", str(root), "--runtime", "opencode"]), 0)
            prompt.assert_not_called()
            self.assertEqual(cli._status_report(root)["skills"]["root"], str(skills))

    def test_checkout_opencode_setup_uses_selected_profile_and_correct_next_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            skills = Path(directory) / "skills"
            output = io.StringIO()
            with patch.object(sys, "argv", [
                "init_agentcaravan.py", "--root", str(root), "--skill-root", str(skills), "--runtime", "opencode",
            ]), patch("builtins.input", side_effect=["", "", ""]), contextlib.redirect_stdout(output):
                self.assertEqual(checkout_init(), 0)
            self.assertEqual(resolve_profile(root)["context"]["runtime_profile_id"], "opencode-information-technology-core-team")
            self.assertTrue((skills / "agent-caravan-opencode-orchestrator").is_dir())
            self.assertIn("Runtime: OpenCode", output.getvalue())
            self.assertNotIn("python3 -m agentcaravan.cli run", output.getvalue())
            self.assertIn("Codex-only", output.getvalue())

    def test_opencode_dry_run_rejects_without_creating_run_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "profile"
            self._init(root, "opencode", Path(directory) / "skills")
            with self.assertRaisesRegex(SystemExit, "Codex-only"), contextlib.redirect_stdout(io.StringIO()):
                cli.main(["run", "--root", str(root), "--dry-run", "--objective", "Check OpenCode"])
            self.assertEqual(list((root / "sessions").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
