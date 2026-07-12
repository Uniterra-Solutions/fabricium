# API Reference

Fabricium is a Python library — not an HTTP service. The API surface is the public Python classes and functions.

## `fabricium.HermesPlugin`

Plugin lifecycle manager. See [Core Module](modules/core.md) for full API.

```python
from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="my-plugin",                          # CLI namespace
    plugin_dir=Path(__file__).parent,          # Plugin root
    default_profile="my-profile",              # None = multi-profile
    soul_md_path="SOUL.md",                    # Relative to plugin_dir
)

def register(ctx):
    plugin.register(ctx)                       # One line = setup/status/update CLI
```

| Method | Description |
|--------|-------------|
| `register(ctx)` | Register CLI commands + bundled skills with Hermes |

## `fabricium.git_utils`

Git subprocess wrappers. See [Git Utils Module](modules/git-utils.md) for full API.

| Function | Returns | Description |
|----------|---------|-------------|
| `is_git_repo(path?)` | `bool` | Is path a git repo? |
| `get_head_hash(path?)` | `str` | SHA of HEAD |
| `get_diff(start, end="HEAD", path?)` | `str` | Diff between refs |
| `get_diff_stat(start, end="HEAD", path?)` | `list[dict]` | Changed files with stats |
| `get_remote_url(path?)` | `str` | Origin URL |
| `get_default_branch(path?)` | `str` | Default branch name |
| `fetch_remote(path?)` | `FetchResult` | Fetch from origin |
| `get_remote_head(path?)` | `str\|None` | Remote HEAD SHA |
| `get_local_head(path?, ref?)` | `str\|None` | Local ref SHA |
| `get_ahead_behind(path?, base?, remote_ref?)` | `AheadBehind` | Ahead/behind counts |
| `is_ancestor(a, b, path?)` | `bool` | Is a ancestor of b? |
| `pull_branch(path?)` | `PullResult` | Fast-forward pull |
| `stage_all(path?)` | `None` | `git add -A` |
| `commit(msg, path?)` | `CommitResult` | Commit staged changes |

## `fabricium.state`

JSON state persistence. See [State Module](modules/state.md) for full API.

| Function | Description |
|----------|-------------|
| `load_state(plugin_name)` | Load `~/.hermes/<name>_state.json` |
| `save_state(plugin_name, state)` | Write state to JSON file |
| `set_profile_state(plugin_name, profile_name, soul_md)` | Record profile setup |
| `get_state_path(plugin_name)` | Path to state file |

## `fabricium.skills`

Bundled skill lifecycle. See [Skills Module](modules/skills.md) for full API.

| Function | Description |
|----------|-------------|
| `is_skill_dir(path)` | True if dir contains SKILL.md |
| `get_bundled_skill_names(plugin_dir)` | Skill names in `skills/` |
| `install_bundled_skills(plugin_dir, target_dir?)` | Copy skills to target |
| `remove_stale_from_profile(profile_skills_dir, stale)` | Remove stale skills (safe) |
| `remove_stale_skills(plugin_dir, after, target_dir?)` | Remove stale skills (**legacy**) |

## `fabricium.prompts`

TTY-aware prompts.

| Function | Description |
|----------|-------------|
| `prompt_yes_no(prompt, default=True)` | Interactive yes/no. Returns `default` if non-TTY |

## `fabricium.testing`

Docker-based integration test environment. See [Testing Module](modules/testing.md) for full API.

| Class | Description |
|-------|-------------|
| `HermesDockerTestEnv` | Docker container + CLI execution |
| `CliResult` | Exit code, stdout, stderr |
| `HermesConfig` | Provider/model config from env |
| `CliAssert` | Composable CLI output assertions |

```python
from fabricium.testing import HermesDockerTestEnv, CliAssert

env = HermesDockerTestEnv(plugin_name="my-plugin", plugin_dir=Path(...))
with env:
    result = env.run_cli("my-plugin", "setup")
    CliAssert.setup_completed(result, "my-plugin")
```

## `fabricium.evals`

Skill evaluation framework. See [Evals Module](modules/evals.md) for full API.

| Class/Function | Description |
|----------------|-------------|
| `SkillEvalHarness` | Docker orchestration for eval pipeline |
| `JudgeClient` | LLM-as-Judge |
| `EvalConfig` | Env-var-driven config |
| `ModelConfig` | Provider + model + credential |
| `EvalTask` | Task definition |
| `RubricSpec` / `RubricDimension` / `ScoringBand` | Rubric types |
| `JudgePrompt` | Judge prompt template |
| `JudgeReport` | Parsed verdict |
| `AgentRunResult` | Agent invocation output |
| `EvalReport` | Evaluation report |
| `calibrate(human, judge)` | Agreement metrics |
| `load_config()` | Build config from env |

```python
from fabricium.evals import SkillEvalHarness, EvalConfig, EvalTask, RubricSpec

config = EvalConfig.from_env()  # or load_config()
harness = SkillEvalHarness(config)
harness.add_profile("bare")
harness.add_profile("jovaltus-agent", setup_commands=["hermes jovaltus setup"])
report = harness.run(tasks, rubric)
```

## How to Update

- New public class/function? → Add to relevant table above.
- Parameter signature changed? → Update the table and link to module doc.
- Module doc expanded? → The canonical API lives in `docs/modules/<name>.md` — this is a summary index.

## Find It Fast

```bash
grep -rn "^def \|^class " src/fabricium/ --include="*.py" | grep -v "^.*__pycache__"
python -c "import fabricium; print(dir(fabricium))"
```
