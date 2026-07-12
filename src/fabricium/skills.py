"""Bundled skill lifecycle management for Hermes plugins.

Handles discovery, installation, and stale-skill cleanup of skills
bundled inside a plugin's skills/ directory.
"""

import shutil
from pathlib import Path

from . import prompts
from .state import _get_global_hermes_home


def is_skill_dir(path: Path) -> bool:
    """Return True if *path* is a directory containing SKILL.md."""
    return path.is_dir() and (path / "SKILL.md").exists()


def get_bundled_skill_names(plugin_dir: Path) -> set[str]:
    """Return the set of skill names currently bundled in the plugin directory."""
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return set()
    return {child.name for child in sorted(skills_dir.iterdir()) if is_skill_dir(child)}


def _remove_installed_skill(skill_name: str) -> bool:
    """Remove an installed skill from the global skills directory.

    Returns True if the skill was removed or didn't exist.
    """
    skill_dir = _get_global_hermes_home() / "skills" / skill_name
    if not skill_dir.exists():
        return True
    try:
        shutil.rmtree(skill_dir)
        print(f"  🗑  Removed stale skill '{skill_name}' from global skills")
        return True
    except OSError as e:
        print(f"  ! Could not remove stale skill '{skill_name}': {e}")
        return False


def remove_stale_skills(
    plugin_dir: Path, after_skills: set[str], target_dir: Path | None = None
) -> None:
    """Detect and remove skills that are no longer bundled.

    When *target_dir* is ``None`` (the default), skills are compared
    against ``~/.hermes/skills/`` for backwards compatibility.
    Pass a profile-specific directory to scope removal to one profile.

    Any skill in *target_dir* that is NOT in *after_skills* is stale.
    """
    if target_dir is None:
        target_dir = _get_global_hermes_home() / "skills"

    if not target_dir.is_dir():
        return

    installed = {child.name for child in target_dir.iterdir() if is_skill_dir(child)}
    stale = installed - after_skills
    if not stale:
        print("  ✓ No stale skills to remove")
        return

    print()
    print("  📋 Stale skills detected (removed from bundle):")
    for name in sorted(stale):
        print(f"    - {name}")

    if prompts.prompt_yes_no("  Remove stale skills?", default=True):
        for name in sorted(stale):
            _remove_installed_skill(name)
    else:
        print("  ⏭  Skipped stale skill removal")


def install_bundled_skills(plugin_dir: Path, target_dir: Path | None = None) -> bool:
    """Copy bundled skills to *target_dir*.

    When *target_dir* is ``None`` (the default), skills are installed to the
    global ``~/.hermes/skills/`` directory for backwards compatibility.
    Pass a profile-specific directory to install skills per-profile.

    Returns True if all skills were installed successfully.
    """
    skills_src = plugin_dir / "skills"
    if not skills_src.is_dir():
        return False

    if target_dir is None:
        target_dir = _get_global_hermes_home() / "skills"

    all_ok = True
    for child in sorted(skills_src.iterdir()):
        if not is_skill_dir(child):
            continue
        skill_md = child / "SKILL.md"
        skill_name = child.name
        dst = target_dir / skill_name / "SKILL.md"

        if dst.exists():
            if dst.read_text() == skill_md.read_text():
                continue  # already up to date — silent
            dst.write_text(skill_md.read_text())
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(skill_md.read_text())
            print(f"  ✓ Skill '{skill_name}' installed to {dst}")
        except OSError as e:
            print(f"  ! Could not install skill '{skill_name}': {e}")
            all_ok = False

    return all_ok
