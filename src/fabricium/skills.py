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




def remove_stale_from_profile(profile_skills_dir: Path, stale: set[str]) -> None:
    """Remove skills that are no longer bundled from a profile's skills directory.

    Unlike the old ``remove_stale_skills``, this does NOT scan the filesystem
    to decide what's stale — the caller provides the exact set of stale skill
    names derived from the plugin's per-profile state.  Only skills that were
    *previously recorded as installed by this plugin* are eligible for removal.
    """
    if not stale:
        return

    print()
    print("  📋 Stale skills detected (removed from bundle):")
    for name in sorted(stale):
        print(f"    - {name}")

    if not prompts.prompt_yes_no("  Remove stale skills?", default=True):
        print("  ⏭  Skipped stale skill removal")
        return

    for name in sorted(stale):
        _remove_skill_from_dir(profile_skills_dir, name)


def _remove_skill_from_dir(skills_dir: Path, skill_name: str) -> None:
    """Delete a skill directory from *skills_dir*."""
    skill_path = skills_dir / skill_name
    if not skill_path.exists():
        return
    try:
        shutil.rmtree(skill_path)
        print(f"  🗑  Removed stale skill '{skill_name}' from {skills_dir}")
    except OSError as e:
        print(f"  ! Could not remove stale skill '{skill_name}': {e}")


# === Backward-compat stub (kept for external callers) ===

def remove_stale_skills(
    plugin_dir: Path, after_skills: set[str], target_dir: Path | None = None
) -> None:
    """Legacy stub — prefer state-based ``remove_stale_from_profile``.

    Scans *target_dir* (default ``~/.hermes/skills/``) and flags skills not
    in *after_skills* as stale.  This can cross-touch other plugins' skills
    when the directory is shared (e.g. the ``default`` profile's global dir).
    """
    if target_dir is None:
        target_dir = _get_global_hermes_home() / "skills"
    if not target_dir.is_dir():
        return
    installed = {child.name for child in target_dir.iterdir() if is_skill_dir(child)}
    stale = installed - after_skills
    if stale:
        print()
        print("  📋 Stale skills detected (removed from bundle):")
        for name in sorted(stale):
            print(f"    - {name}")
        if prompts.prompt_yes_no("  Remove stale skills?", default=True):
            for name in sorted(stale):
                _remove_skill_from_dir(target_dir, name)


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
        skill_name = child.name
        dst_dir = target_dir / skill_name

        try:
            shutil.copytree(child, dst_dir, dirs_exist_ok=True)
            print(f"  ✓ Skill '{skill_name}' installed to {dst_dir}")
        except OSError as e:
            print(f"  ! Could not install skill '{skill_name}': {e}")
            all_ok = False

    return all_ok
