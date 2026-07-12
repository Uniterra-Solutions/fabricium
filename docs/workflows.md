# Workflows

Step-by-step recipes for common development tasks.

## Release a New Version

1. Update version in `pyproject.toml:3`
2. Update `CHANGELOG.md` with the new version section
3. Commit: `git commit -m "release: vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push origin main --tags`
6. PyPI publishes automatically via OIDC Trusted Publishing

## Add a Public API Function

1. Add function to the relevant module in `src/fabricium/`
2. Re-export in the module's `__init__.py` + `__all__`
3. Add tests in `tests/test_<module>.py`
4. Run: `uv run pytest tests/test_<module>.py -v`
5. Update `docs/modules/<module>.md` — add to public API table
6. Update `docs/api-reference.md` — add to summary table

## Add a New Module to `fabricium.evals`

1. Create `src/fabricium/evals/<new_module>.py`
2. Import + re-export in `src/fabricium/evals/__init__.py`
3. Add `__all__` entry
4. Add tests in `tests/test_evals_<new_module>.py`
5. Run: `uv run pytest tests/ -v`
6. Run: `uv run ruff check . && uv run mypy`
7. Add module doc to `docs/modules/<new_module>.md`
8. Update `docs/api-reference.md` — add to evals table

## Run the Eval Pipeline

```bash
export EVAL_CANDIDATE_PROVIDER=deepseek
export EVAL_CANDIDATE_MODEL=deepseek/deepseek-chat
export EVAL_CANDIDATE_API_KEY=sk-...
export EVAL_JUDGE_PROVIDER=anthropic
export EVAL_JUDGE_MODEL=anthropic/claude-sonnet-4
export EVAL_JUDGE_API_KEY=sk-ant-...
export EVAL_JOVALTUS_PLUGIN_DIR=/path/to/jovaltus

# All tasks
python -m fabricium.evals.runner

# Specific task
EVAL_TASKS=python-backend python -m fabricium.evals.runner
```

Reports in `eval_results/report_<task>_<timestamp>.json`.

## Debug a Failing Integration Test

1. Set `FABRICIUM_TEST_KEEP=1` to preserve the container
2. Run the failing test: `uv run pytest tests/integration/test_cli.py::<test> -v`
3. Inspect the container: `docker exec -it fabricium-test-<plugin>-<pid> bash`
4. Manually run CLI commands inside: `hermes <plugin> setup`
5. When done: `docker rm -f fabricium-test-<plugin>-<pid>`

## Build a Plugin with Fabricium

1. Create plugin structure:
   ```
   my-plugin/
   ├── plugin.yaml              # or pyproject.toml with entry point
   ├── __init__.py              # register(ctx) entry point
   ├── skills/                  # Bundled skills
   │   └── my-skill/SKILL.md
   └── SOUL.md                  # Agent identity (optional)
   ```
2. In `__init__.py`:
   ```python
   from pathlib import Path
   from fabricium import HermesPlugin

   plugin = HermesPlugin(
       name="my-plugin",
       plugin_dir=Path(__file__).parent,
       default_profile="my-profile",
   )

   def register(ctx):
       plugin.register(ctx)
       # ... register unique tools ...
   ```
3. Test locally: `hermes my-plugin setup`
4. Write integration tests using `fabricium.testing.HermesDockerTestEnv`

## How to Update

- New workflow? → Add recipe following the format above.
- Workflow changed? → Update the steps.
- Command deprecated? → Replace with new command.

## Find It Fast

```bash
grep "release:" CHANGELOG.md  # All release commits
grep "version = " pyproject.toml  # Current version
```
