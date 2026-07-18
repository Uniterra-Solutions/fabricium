# Changelog

All notable changes to Fabricium will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.7] — 2026-07-18

### Added

- **Dynamic Hermes home resolution via CLI.** `_get_global_hermes_home()` now falls back to `hermes config path` before `Path.home() / ".hermes"`, providing cross-platform path resolution without hardcoded conventions. The CLI result is cached at module level to avoid repeated subprocess calls. New functions: `_derive_global_home_from_config_path()`, `_resolve_hermes_home_via_cli()`.

## [0.1.6] — 2026-07-12

### Fixed

- **`assert_update_check_responded` now accepts pip-installed plugin output.** When a plugin is installed via pip (rather than git-cloned), `update --check` prints pip upgrade instructions. The assertion now recognizes `"pip-installed plugin"` as valid diagnostic output alongside the existing git-mode messages.

## [0.1.5] — 2026-07-12

### Fixed

- **`install_bundled_skills` now copies the entire skill directory**, not just `SKILL.md`. Previously, auxiliary files (`references/`, `scripts/`, `templates/`, config files) were silently dropped during sync. Replaced single-file copy with `shutil.copytree` so all bundled skill files are installed and updated correctly.

## [0.1.1] — 2026-07-12

### Changed

- **PyPI publishing via OIDC Trusted Publishing** — no API token required; release workflow binds to the GitHub repo via PyPI's pending publisher

## [0.1.0] — 2026-07-12

### Added

- **`HermesPlugin` class** — one-line plugin lifecycle registration: `setup`, `status`, `update`, `update --check`
- **Single-profile and multi-profile modes** — `default_profile="my-profile"` or `default_profile=None`
- **`fabricium.git_utils`** — Git subprocess wrappers: `fetch_remote`, `pull_branch`, `get_ahead_behind`, `get_diff`, `get_diff_stat`, `is_ancestor`, `stage_all`, `commit`, and more
- **`fabricium.state`** — JSON state persistence: `load_state`, `save_state`, `set_profile_state`
- **`fabricium.skills`** — Bundled skill lifecycle: `install_bundled_skills`, `remove_stale_skills`, `get_bundled_skill_names`
- **`fabricium.prompts`** — TTY-aware prompt utilities: `prompt_yes_no`
- **`fabricium.evals`** — Complete skill evaluation framework:
  - `SkillEvalHarness` — Docker-based evaluation orchestrator
  - `JudgeClient` — LLM-as-Judge with cross-provider support (Anthropic, OpenAI-compatible)
  - `EvalConfig` — Environment-variable-driven configuration
  - `EvalTask` / `RubricSpec` / `RubricDimension` / `ScoringBand` — task and rubric building blocks
  - `calibrate()` — Judge-human agreement metrics (Cohen's κ, Spearman ρ)
  - `JudgePrompt` — Customizable judge prompt templates
  - Built-in example tasks and rubrics for Jovaltus evaluation
  - Reasoning-model SSE proxy for DeepSeek V4 compatibility
- **`fabricium.testing`** — Docker-based integration test environment:
  - `HermesDockerTestEnv` — Disposable Hermes container for CLI testing
  - `CliAssert` — Composable CLI output assertions
  - `HermesConfig` — Provider/model configuration for test environments

### Internals

- 104 tests covering plugin lifecycle, git utilities, state persistence, skill management, and CLI assertions
- ruff (E, F, I, N, W) + mypy `--strict` + pytest quality gates
- MIT license
- Conventional Commits history from initial extraction through eval pipeline refinements
