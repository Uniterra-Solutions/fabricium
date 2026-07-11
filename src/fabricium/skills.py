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
    return {
        child.name for child in sorted(skills_dir.iterdir()) if is_skill_dir(child)
    }


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


def remove_stale_skills(plugin_dir: Path, after_skills: set[str]) -> None:
    """Detect and remove skills that are no longer bundled.

    Compares currently installed skills against the new set of bundled
    skills. Any skill installed in ~/.hermes/skills/ that no longer
    exists in the plugin is stale and gets removed.
    """
    global_dir = _get_global_hermes_home() / "skills"
    if not global_dir.is_dir():
        return

    installed = {child.name for child in global_dir.iterdir() if is_skill_dir(child)}
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


def install_bundled_skills(plugin_dir: Path) -> bool:
    """Copy bundled skills to the global skills dir for visibility.

    Returns True if all skills were installed successfully.
    """
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        print("  ! No bundled skills directory found")
        return False

    all_ok = True
    for child in sorted(skills_dir.iterdir()):
        if not is_skill_dir(child):
            continue
        skill_md = child / "SKILL.md"
        skill_name = child.name
        dst = _get_global_hermes_home() / "skills" / skill_name / "SKILL.md"

        if dst.exists():
            if dst.read_text() == skill_md.read_text():
                print(f"  ✓ Skill '{skill_name}' already installed and up to date")
                continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(skill_md.read_text())
            print(f"  ✓ Skill '{skill_name}' installed to {dst}")
            print(f"    Load via: skill_view('{skill_name}')")
        except OSError as e:
            print(f"  ! Could not install skill '{skill_name}': {e}")
            all_ok = False

    return all_ok
