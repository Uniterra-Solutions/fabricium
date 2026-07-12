"""Fabricium — Shared Hermes plugin infrastructure.

Provides the HermesPlugin class that wraps plugin lifecycle management:
CLI commands (setup, status, update), bundled skill installation,
Git self-update, and state persistence. Plugin authors focus on their
unique tools and hooks; Fabricium handles the boilerplate.

Usage::

    from pathlib import Path
    from fabricium import HermesPlugin

    plugin = HermesPlugin(
        name="my-plugin",
        plugin_dir=Path(__file__).parent,
        default_profile="my-profile",   # None = multi-profile mode
    )

    def register(ctx):
        plugin.register(ctx)
        # ... register unique tools here ...
"""

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import git_utils, prompts, skills, state

logger = logging.getLogger(__name__)


def _print_pip_upgrade_instructions(name: str) -> None:
    """Print upgrade instructions for pip-installed plugins."""
    print(f"🔍 pip-installed plugin — check for updates with:")
    print(f"   pip install --upgrade {name}")
    print(f"   Then run: hermes {name} update  (to refresh skills)")


class HermesPlugin:
    """Hermes plugin lifecycle manager.

    Handles CLI registration (setup/status/update), bundled skill
    lifecycle, SOUL.md deployment, and JSON state persistence.

    Parameters
    ----------
    name:
        Plugin name used for CLI namespace and state file.
        E.g. ``"caelterra"`` → ``hermes caelterra setup``,
        ``~/.hermes/caelterra_state.json``.
    plugin_dir:
        Path to the plugin's root directory (where ``__init__.py`` lives).
        Used to locate ``skills/`` and ``SOUL.md``.
    default_profile:
        Profile name for single-profile plugins (e.g. ``"jovaltus-agent"``).
        When ``None``, enters multi-profile mode: setup lists all available
        profiles and lets the user choose.
    soul_md_path:
        Path to SOUL.md relative to *plugin_dir*. Defaults to ``"SOUL.md"``.
    """

    def __init__(
        self,
        name: str,
        plugin_dir: Path,
        default_profile: str | None = None,
        soul_md_path: str = "SOUL.md",
    ) -> None:
        self.name = name
        self.plugin_dir = plugin_dir
        self.default_profile = default_profile
        self.soul_md_path = soul_md_path

    # ── Public API ──────────────────────────────────────────────────

    def register(self, ctx: Any) -> None:
        """Register CLI commands and bundled skills with Hermes.

        Call this once from your plugin's ``register(ctx)`` function.
        After calling, you can register additional plugin-specific
        tools, hooks, or commands.
        """
        self._register_cli(ctx)
        self._register_bundled_skills(ctx)

    # ── Path helpers ────────────────────────────────────────────────

    def _get_profiles_dir(self) -> Path:
        """Return the global Hermes profiles directory."""
        return state._get_global_hermes_home() / "profiles"

    def _get_profile_dir(self, profile_name: str) -> Path:
        """Return the profile directory for a given profile name.

        The 'default' profile is special — its home is the global Hermes
        directory (~/.hermes/), not a subdirectory of profiles/.
        """
        if profile_name == "default":
            return state._get_global_hermes_home()
        return self._get_profiles_dir() / profile_name

    # ── Profile helpers ─────────────────────────────────────────────

    def _list_profiles(self) -> list[str]:
        """List all available Hermes profile names.

        Scans the profiles dir for named profiles, and always includes
        'default' (whose config lives at ~/.hermes/config.yaml).
        """
        profiles: list[str] = []
        profiles_dir = self._get_profiles_dir()
        if profiles_dir.is_dir():
            profiles.extend(
                child.name
                for child in sorted(profiles_dir.iterdir())
                if child.is_dir() and (child / "config.yaml").exists()
            )
        # default profile uses ~/.hermes/config.yaml, not a subdirectory
        if state._get_global_hermes_home().joinpath("config.yaml").exists():
            profiles.insert(0, "default")
        return profiles

    def _ensure_profile(self, profile_name: str) -> bool:
        """Create the profile if it doesn't exist.

        Returns True if the profile exists or was created.
        """
        profile_dir = self._get_profile_dir(profile_name)
        if profile_dir.exists() and (profile_dir / "config.yaml").exists():
            return True

        print(f"\n  Creating profile '{profile_name}'...")
        try:
            subprocess.run(
                ["hermes", "profile", "create", profile_name],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"  ✓ Profile '{profile_name}' created")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ! Could not auto-create profile: {e.stderr.strip()}")
            print(f"    Create it manually: hermes profile create {profile_name}")
            return False
        except FileNotFoundError:
            print("  ! 'hermes' CLI not found on PATH")
            print(f"    Create the profile manually: hermes profile create {profile_name}")
            return False

    def _apply_soul_md(self, profile_name: str) -> bool:
        """Write SOUL.md from the plugin bundle into the profile directory."""
        profile_dir = self._get_profile_dir(profile_name)
        soul_src = self.plugin_dir / self.soul_md_path
        soul_dst = profile_dir / "SOUL.md"

        if not soul_src.exists():
            print(f"  ! Bundled SOUL.md not found at {soul_src}")
            return False

        try:
            soul_dst.write_text(soul_src.read_text())
            print(f"  ✓ SOUL.md written to {soul_dst}")
            return True
        except OSError as e:
            print(f"  ! Could not write SOUL.md: {e}")
            return False

    # ── Multi-profile selector ──────────────────────────────────────

    def _prompt_select_profiles(self, available: list[str]) -> list[str]:
        """Interactive multi-select prompt for profiles.

        In non-TTY mode returns all profiles.
        """
        if not sys.stdin.isatty():
            return list(available)

        print("\n📁 Available profiles:")
        for i, name in enumerate(available, 1):
            print(f"   {i}) {name}")
        print()

        raw = input("  Select profiles (comma-separated numbers, or 'all'): ").strip().lower()
        if not raw or raw == "all":
            return list(available)

        selected: list[str] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(available):
                    selected.append(available[idx])

        return selected or list(available)

    # ── State helpers ───────────────────────────────────────────────

    def _load_state(self) -> dict[str, Any]:
        return state.load_state(self.name)

    def _save_state(self, s: dict[str, Any]) -> None:
        state.save_state(self.name, s)

    def _set_profile_state(self, profile_name: str, soul_md: bool) -> None:
        state.set_profile_state(self.name, profile_name, soul_md)

    # ── Sync installed profiles ──────────────────────────────────────

    def _sync_installed_profiles(self, context: str = "") -> None:
        """Update skills and SOUL.md for all profiles in the installation state."""
        s = self._load_state()
        profiles_state = s.get("profiles", {})

        if not profiles_state:
            print("\n  No profiles in installation state.")
            print(f"  Run: hermes {self.name} setup")
            return

        ctx = f" ({context})" if context else ""
        print(f"\n{'─' * 40}")
        print(f"🔄 Syncing profiles{ctx}")

        ts = datetime.now().isoformat(timespec="seconds")

        synced = 0
        for profile_name, info in sorted(profiles_state.items()):
            profile_dir = self._get_profile_dir(profile_name)
            if not profile_dir.exists() or not (profile_dir / "config.yaml").exists():
                print(f"\n  ⏭  Profile '{profile_name}' no longer exists — skipping")
                continue

            print(f"\n📁 Profile: {profile_name}")

            if info.get("soul_md"):
                print("  🧠 Updating SOUL.md...")
                self._apply_soul_md(profile_name)
            else:
                print("  ✓ Skills only (SOUL.md not tracked)")

            s["profiles"][profile_name]["updated_at"] = ts
            synced += 1

        self._save_state(s)
        print(f"\n  ✅ {synced} profile(s) synced")

    # ── CLI handlers ────────────────────────────────────────────────

    def _setup_command(self, args: Any) -> None:  # noqa: ARG002
        """Handler for 'hermes <name> setup'."""
        print(f"⚡ {self.name.title()} Setup")
        print("━" * 40)

        if self.default_profile:
            self._setup_single_profile()
        else:
            self._setup_multi_profile()

    def _setup_single_profile(self) -> None:
        """Setup for single-profile plugins."""
        profile_name = self.default_profile
        assert profile_name is not None

        # Step 1: Profile
        print("\n📁 Profile")
        profile_ok = self._ensure_profile(profile_name)
        if profile_ok:
            print(f"  ✓ Profile '{profile_name}' ready")

        # Step 2: Bundled skills
        print("\n📚 Bundled Skills")
        with_skills = prompts.prompt_yes_no("  Install bundled skills?", default=True)
        if with_skills:
            skills.install_bundled_skills(self.plugin_dir)
        else:
            print("  ⏭  Skipped skill installation")

        # Step 3: SOUL.md
        print("\n🧠 Agent Identity (SOUL.md)")
        profile_dir = self._get_profile_dir(profile_name)
        soul_dst = profile_dir / "SOUL.md"
        with_soul = prompts.prompt_yes_no(
            f"  Apply SOUL.md with {self.name.title()} agent identity?", default=True
        )
        if with_soul and soul_dst.exists():
            if not prompts.prompt_yes_no("  Overwrite existing SOUL.md?", default=False):
                print("  ⏭  Keeping existing SOUL.md")
                with_soul = False
        if with_soul:
            self._apply_soul_md(profile_name)
        else:
            print("  ⏭  Skipped SOUL.md")

        self._set_profile_state(profile_name, soul_md=with_soul)

        print(f"\n{'━' * 40}")
        print(f"✅ {self.name.title()} setup complete.")
        print(f"  CLI commands:      hermes {self.name} <setup|status|update>")
        print(f"  Check status:      hermes {self.name} status")
        print(f"  Check for updates: hermes {self.name} update --check")

    def _setup_multi_profile(self) -> None:
        """Setup for multi-profile plugins."""
        available = self._list_profiles()
        if not available:
            print("\n! No Hermes profiles found.")
            print("  Create one first: hermes profile create <name>")
            return

        selected = self._prompt_select_profiles(available)
        if not selected:
            print("\n  ⏭  No profiles selected — exiting.")
            return

        print(f"\n  Selected profiles: {', '.join(selected)}")

        print("\n📦 Installation mode:")
        if prompts.prompt_yes_no("  Install SOUL.md with agent identity?", default=True):
            mode = "soul_md"
            print("  ✓ Mode: Skills + SOUL.md")
        else:
            mode = "skills_only"
            print("  ✓ Mode: Skills only")

        any_ok = False
        for profile_name in selected:
            print(f"\n{'─' * 40}")
            print(f"📁 Profile: {profile_name}")

            profile_ok = self._ensure_profile(profile_name)
            if not profile_ok:
                print(f"  ⏭  Skipping profile '{profile_name}'")
                continue

            print()
            skills.install_bundled_skills(self.plugin_dir)

            soul_ok = True
            if mode == "soul_md":
                print()
                profile_dir = self._get_profile_dir(profile_name)
                soul_dst = profile_dir / "SOUL.md"
                if soul_dst.exists():
                    if prompts.prompt_yes_no("  Overwrite existing SOUL.md?", default=False):
                        soul_ok = self._apply_soul_md(profile_name)
                    else:
                        print("  ⏭  Keeping existing SOUL.md")
                else:
                    soul_ok = self._apply_soul_md(profile_name)

            self._set_profile_state(profile_name, soul_md=(mode == "soul_md" and soul_ok))
            any_ok = True

        print(f"\n{'━' * 40}")
        if any_ok:
            print(f"✅ {self.name.title()} setup complete for selected profiles.")
            print(f"  Check status: hermes {self.name} status")
            print(f"  Update:       hermes {self.name} update")
        else:
            print("⚠️  Setup incomplete.")

    def _status_command(self, args: Any) -> None:  # noqa: ARG002
        """Handler for 'hermes <name> status'."""
        print(f"📊 {self.name.title()} Installation Status")
        print("━" * 40)

        s = self._load_state()
        profiles_state = s.get("profiles", {})

        if not profiles_state:
            print(f"\n  {self.name.title()} has not been installed to any profile yet.")
            print(f"  Run: hermes {self.name} setup")
            return

        print()
        header = f"{'Profile':<22} {'Status':<24} {'Last Updated'}"
        sep = f"{'─' * 22} {'─' * 24} {'─' * 20}"
        print(f"  {header}")
        print(f"  {sep}")
        for pname, info in sorted(profiles_state.items()):
            status = "Skills + SOUL.md ✓" if info.get("soul_md") else "Skills only"
            updated = info.get("updated_at", "—")
            print(f"  {pname:<22} {status:<24} {updated}")
        print()

        if self.default_profile is None:
            all_profiles = self._list_profiles()
            missing = [p for p in all_profiles if p not in profiles_state]
            if missing:
                print("  📋 Profiles without Caelterra:")
                for pname in missing:
                    print(f"    - {pname}")
                print("  Run: hermes caelterra setup")

    def _update_check(self, args: Any) -> None:  # noqa: ARG002
        """Handler for 'hermes <name> update --check'.

        Checks for newer plugin versions.  For git-installed plugins
        this compares against the remote.  For pip-installed plugins
        it reports the installed version and suggests ``pip install --upgrade``.
        """
        project_dir = str(self.plugin_dir.resolve())

        if not git_utils.is_git_repo(project_dir):
            _print_pip_upgrade_instructions(self.name)
            return

        remote_url = git_utils.get_remote_url(project_dir)
        if not remote_url:
            _print_pip_upgrade_instructions(self.name)
            return

        print(f"🔍 Checking for {self.name.title()} updates...")
        print(f"   Remote: {remote_url}")

        local_head = git_utils.get_local_head(project_dir)

        print("   Fetching remote refs...", end=" ", flush=True)
        fetch_result = git_utils.fetch_remote(project_dir)
        print("✓" if fetch_result["success"] else "✗")

        if not fetch_result["success"]:
            print(f"   Fetch failed: {fetch_result['message']}")
            return

        info = git_utils.get_ahead_behind(project_dir)
        remote_head = info.get("remote_head")

        if remote_head is None:
            print("! Could not determine remote HEAD.")
            return

        behind = info.get("behind", 0)
        ahead = info.get("ahead", 0)

        print(f"\n   Local:  {local_head[:12] if local_head else 'unknown'}")
        print(f"   Remote: {remote_head[:12]}")

        if behind > 0:
            print(f"\n📦 {behind} new commit(s) behind remote.")
            print(f"   Run 'hermes {self.name} update' to pull the latest changes.")
        elif ahead > 0:
            print(f"\n⚠️  Local is {ahead} commit(s) AHEAD of remote.")
            print("   (You have local changes not yet pushed.)")
        else:
            print(f"\n✅ {self.name.title()} is up to date.")

    def _update_pull(self, args: Any) -> None:  # noqa: ARG002
        """Handler for 'hermes <name> update'.

        Always refreshes bundled skills and syncs profiles, even when
        the plugin was installed via pip (no git repo).  Git pull is
        attempted opportunistically and skipped when not applicable.
        """
        project_dir = str(self.plugin_dir.resolve())

        print(f"📦 Updating {self.name.title()}...")

        # ── Try git pull (optional — skipped for pip installs) ──────
        did_pull = False
        if git_utils.is_git_repo(project_dir):
            remote_url = git_utils.get_remote_url(project_dir)
            if remote_url:
                print(f"   Remote: {remote_url}")

                # Guard against uncommitted changes
                try:
                    raw_status = subprocess.check_output(
                        ["git", "-C", project_dir, "status", "--porcelain"],
                        text=True,
                    ).strip()
                except subprocess.CalledProcessError:
                    raw_status = ""
                if raw_status:
                    print(
                        "\n! You have uncommitted changes."
                        " Stash or commit them first:"
                    )
                    for line in raw_status.splitlines():
                        print(f"   {line}")
                    print(f"\n  Then run: hermes {self.name} update")
                    # Don't return — still refresh skills below
                else:
                    # Fetch and pull
                    print("   Fetching remote refs...", end=" ", flush=True)
                    fetch_result = git_utils.fetch_remote(project_dir)
                    print("✓" if fetch_result["success"] else "✗")

                    if fetch_result["success"]:
                        info = git_utils.get_ahead_behind(project_dir)
                        behind = info.get("behind", 0)
                        local_head = git_utils.get_local_head(project_dir)
                        print(f"   Local:  {local_head[:12] if local_head else 'unknown'}")

                        if behind == 0:
                            print("   Remote: already up to date")
                        else:
                            print(f"   Pulling {behind} new commit(s)...")
                            result = git_utils.pull_branch(project_dir)
                            if result["success"]:
                                after = result.get("after", "")
                                print(f"   After:  {after[:12] if after else 'unknown'}")
                                did_pull = True
                            else:
                                print(f"\n   ✗ Pull failed: {result['message']}")
            else:
                print("   ! No remote — skipping git update")
        else:
            print("   ℹ pip install — skipping git update")

        # ── Always refresh skills and sync profiles ─────────────────
        print("\n📚 Updating bundled skills...")

        # Remove skills that no longer exist in the plugin source
        after_skills = skills.get_bundled_skill_names(self.plugin_dir)
        skills.remove_stale_skills(self.plugin_dir, after_skills)

        skills.install_bundled_skills(self.plugin_dir)
        self._sync_installed_profiles("updated" if did_pull else "refreshed")

        print(f"\n{'━' * 40}")
        print(f"✅ {self.name.title()} update complete.")
        print(f"   Check status: hermes {self.name} status")

    # ── CLI command dispatch ────────────────────────────────────────

    def _dispatch(self, args: Any) -> None:
        """Top-level dispatcher for 'hermes <name> <subcommand>'."""
        sub = getattr(args, f"{self.name}_command", None)

        if sub in ("setup", None):
            self._setup_command(args)
        elif sub == "status":
            self._status_command(args)
        elif sub == "update":
            if getattr(args, "check", False):
                self._update_check(args)
            else:
                self._update_pull(args)
        else:
            print(f"Unknown command: {sub}")
            print(f"Usage: hermes {self.name} <setup|status|update>")

    def _setup_argparse(self, subparser: Any) -> None:
        """Build argparse subcommand tree for 'hermes <name>'."""
        subs = subparser.add_subparsers(dest=f"{self.name}_command")

        subs.add_parser(
            "setup",
            help=f"Install {self.name.title()} skills and optionally SOUL.md",
        )

        subs.add_parser(
            "status",
            help=f"Show {self.name.title()} installation status per profile",
        )

        update_parser = subs.add_parser(
            "update",
            help=f"Check for and apply {self.name.title()} plugin updates",
        )
        update_parser.add_argument(
            "--check",
            action="store_true",
            help="Only check for updates without pulling",
        )

        subparser.set_defaults(func=self._dispatch)

    def _register_cli(self, ctx: Any) -> None:
        """Register CLI commands for this plugin."""
        ctx.register_cli_command(
            name=self.name,
            help=f"{self.name.title()} plugin — setup, status, update, and skill management",
            setup_fn=self._setup_argparse,
            handler_fn=self._dispatch,
        )

    def _register_bundled_skills(self, ctx: Any) -> None:
        """Register bundled skills from the plugin's skills/ directory."""
        skills_dir = self.plugin_dir / "skills"
        if skills_dir.is_dir():
            for child in sorted(skills_dir.iterdir()):
                skill_md = child / "SKILL.md"
                if child.is_dir() and skill_md.exists():
                    ctx.register_skill(child.name, skill_md)
                    logger.info("Registered bundled skill: %s:%s", self.name, child.name)
