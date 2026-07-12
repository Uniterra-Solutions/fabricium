# Project Structure

```
fabricium/
├── pyproject.toml          # Build config, dev deps, tool settings
├── uv.lock                 # Pinned dependency tree
├── README.md               # User-facing documentation
├── CHANGELOG.md            # Release history (Keep a Changelog)
├── LICENSE                 # MIT
├── docs/
│   └── fabricium-proposal.md  # Original design proposal (reference)
├── src/
│   └── fabricium/          # Library source
│       ├── __init__.py     # HermesPlugin class (core lifecycle)
│       ├── skills.py       # Bundled skill discovery, install, cleanup
│       ├── state.py        # JSON state persistence
│       ├── prompts.py      # TTY-aware yes/no prompts
│       ├── git_utils.py    # Git subprocess wrappers
│       ├── testing/        # Docker-based integration test env
│       │   ├── harness.py  # HermesDockerTestEnv, CliResult, HermesConfig
│       │   ├── assertions.py # CliAssert: composable CLI-output checks
│       │   └── fixtures.py # Pytest fixtures for plugin tests
│       └── evals/          # Skill evaluation framework
│           ├── config.py   # EvalConfig, ModelConfig, load_config()
│           ├── harness.py  # SkillEvalHarness, AgentRunResult, EvalReport
│           ├── judge.py    # JudgeClient, JudgePrompt, calibrate()
│           ├── tasks.py    # EvalTask dataclass
│           ├── rubrics.py  # ScoringBand, RubricDimension, RubricSpec
│           ├── runner.py   # CLI runner: python -m fabricium.evals.runner
│           ├── proxy.py    # DeepSeek V4 SSE reasoning proxy
│           ├── example_tasks.py   # Reference Jovaltus eval tasks
│           └── example_rubrics.py # Reference Jovaltus eval rubrics
└── tests/
    ├── conftest.py         # Shared pytest fixtures (tmp_plugin_dir etc.)
    ├── test_plugin.py      # HermesPlugin lifecycle tests
    ├── test_skills.py      # Skill install/discovery/stale-cleanup tests
    ├── test_state.py       # State persistence tests
    ├── test_git_utils.py   # Git utility tests
    ├── test_assertions.py  # CliAssert unit tests
    └── integration/
        ├── conftest.py     # Docker test env fixture
        ├── test_cli.py     # End-to-end CLI integration tests
        └── test_plugin/    # Minimal test plugin for integration
            └── __init__.py # register() for integration tests
```

## Directory Responsibilities

| Directory | Responsibility | Key Files |
|-----------|----------------|-----------|
| `src/fabricium/` | Core library: plugin lifecycle, state, git, skills | `__init__.py`, `git_utils.py` |
| `src/fabricium/testing/` | Docker test harness for plugin CI | `harness.py`, `assertions.py` |
| `src/fabricium/evals/` | LLM-as-Judge skill evaluation pipeline | `harness.py`, `judge.py`, `runner.py` |
| `tests/` | Unit + integration tests (104 total) | `conftest.py`, `test_plugin.py` |
| `tests/integration/` | Docker-based end-to-end CLI tests | `test_cli.py`, `conftest.py` |

## How to Update

- New module added? → Add to directory tree + responsibilities table.
- File renamed? → Update tree and cross-references in module docs.
- New top-level dir? → Add to tree and assess whether it needs a module doc.

## Find It Fast

```bash
ls src/fabricium/                # Top-level modules
ls src/fabricium/testing/        # Test harness files
ls src/fabricium/evals/          # Eval framework files
grep -r "def " src/fabricium/ --include="*.py" | head  # All public functions
```
