"""Tests for fabricium.skills."""

import shutil

from fabricium import skills
from fabricium.state import _get_global_hermes_home


class TestIsSkillDir:
    def test_returns_true_for_skill_dir(self, tmp_plugin_dir):
        skill_dir = tmp_plugin_dir / "skills" / "skill-a"
        assert skills.is_skill_dir(skill_dir) is True

    def test_returns_false_for_non_dir(self, tmp_plugin_dir):
        file_path = tmp_plugin_dir / "SOUL.md"
        assert skills.is_skill_dir(file_path) is False

    def test_returns_false_for_dir_without_skill_md(self, tmp_plugin_dir):
        empty_dir = tmp_plugin_dir / "empty"
        empty_dir.mkdir()
        assert skills.is_skill_dir(empty_dir) is False


class TestGetBundledSkillNames:
    def test_returns_all_skill_dirs(self, tmp_plugin_dir):
        names = skills.get_bundled_skill_names(tmp_plugin_dir)
        assert names == {"skill-a", "skill-b"}

    def test_returns_empty_for_missing_skills_dir(self, tmp_plugin_dir):
        shutil.rmtree(tmp_plugin_dir / "skills")
        names = skills.get_bundled_skill_names(tmp_plugin_dir)
        assert names == set()

    def test_ignores_non_skill_dirs(self, tmp_plugin_dir):
        (tmp_plugin_dir / "skills" / "not-a-skill").mkdir()
        names = skills.get_bundled_skill_names(tmp_plugin_dir)
        assert "not-a-skill" not in names


class TestInstallBundledSkills:
    def test_installs_skills_to_global_dir(self, tmp_plugin_dir):
        global_skills = _get_global_hermes_home() / "skills"
        result = skills.install_bundled_skills(tmp_plugin_dir)
        assert result is True
        assert (global_skills / "skill-a" / "SKILL.md").exists()
        assert (global_skills / "skill-b" / "SKILL.md").exists()

    def test_second_install_is_idempotent(self, tmp_plugin_dir):
        skills.install_bundled_skills(tmp_plugin_dir)
        result = skills.install_bundled_skills(tmp_plugin_dir)
        assert result is True

    def test_updates_changed_skill(self, tmp_plugin_dir):
        skills.install_bundled_skills(tmp_plugin_dir)
        # Modify bundled skill
        skill_md = tmp_plugin_dir / "skills" / "skill-a" / "SKILL.md"
        skill_md.write_text("---\nname: skill-a\n---\n# Updated\n")
        result = skills.install_bundled_skills(tmp_plugin_dir)
        assert result is True

    def test_copies_auxiliary_skill_files(self, tmp_plugin_dir):
        """install_bundled_skills copies REFERENCES, scripts, and other files."""
        # Add auxiliary files to skill-a
        skill_dir = tmp_plugin_dir / "skills" / "skill-a"
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "api.md").write_text("# API\n")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "setup.sh").write_text("#!/bin/bash\necho setup\n")

        target = tmp_plugin_dir.parent / "skills"
        skills.install_bundled_skills(tmp_plugin_dir, target)

        dst = target / "skill-a"
        assert dst.is_dir()
        assert (dst / "SKILL.md").exists()
        assert (dst / "references").is_dir()
        assert (dst / "references" / "api.md").read_text() == "# API\n"
        assert (dst / "scripts").is_dir()
        assert (dst / "scripts" / "setup.sh").read_text() == "#!/bin/bash\necho setup\n"


class TestRemoveStaleSkills:
    def test_no_stale_when_all_match(self, tmp_plugin_dir):
        skills.install_bundled_skills(tmp_plugin_dir)
        current = skills.get_bundled_skill_names(tmp_plugin_dir)
        # Should not raise
        skills.remove_stale_skills(tmp_plugin_dir, current)

    def test_detects_stale_skills(self, tmp_plugin_dir):
        # Install bundled skills
        skills.install_bundled_skills(tmp_plugin_dir)
        # Now claim only skill-a is bundled
        skills.remove_stale_skills(tmp_plugin_dir, {"skill-a"})
        # skill-b should be removed
        global_skills = _get_global_hermes_home() / "skills"
        assert not (global_skills / "skill-b" / "SKILL.md").exists()
