# Technology Stack

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| Python | ≥ 3.10 | Runtime | Target 3.10 for broad compatibility |
| hatchling | — | Build system | PEP 621 pyproject.toml, src layout |
| uv | — | Package manager, venv | Lockfile: `uv.lock` |
| pytest | ≥ 8 | Test framework | `tests/` directory, 104 tests |
| ruff | ≥ 0.8 | Linter + formatter | Rules: E, F, I, N, W; line-length 100 |
| mypy | ≥ 1.16 | Static type checker | `--strict` mode, `src/fabricium` files |

## Runtime Dependencies

**None.** Fabricium targets zero runtime dependencies — pure Python standard library. All subprocess calls use `subprocess.run()`; HTTP calls in `fabricium.evals.judge` use `urllib.request`.

## Infrastructure (optional, for testing/eval)

| Component | Purpose | Required By |
|-----------|---------|-------------|
| Docker | Container runtime | `fabricium.testing`, `fabricium.evals` |
| `nousresearch/hermes-agent:latest` | Hermes Docker image | Both test and eval harnesses |

## External Services (optional)

| Service | Purpose | Used By |
|---------|---------|---------|
| Anthropic API | LLM judge | `fabricium.evals.judge.JudgeClient` |
| OpenAI-compatible API | LLM judge | `fabricium.evals.judge.JudgeClient` |
| DeepSeek API | Candidate agent | `fabricium.evals.runner` |

## How to Update

- New dev dependency? → Add row above + update `pyproject.toml`
- Runtime dependency added? → Major decision — fabricium is deliberately dependency-free. Update the "Runtime Dependencies" section and document rationale.
- Python version floor raised? → Update `requires-python` in `pyproject.toml:5` and the version row above.
- New Docker image? → Update infrastructure table.

## Find It Fast

```bash
grep "requires-python" pyproject.toml              # Python version
grep "dependencies" pyproject.toml                  # Runtime deps (should be empty)
grep -E "^dev = " pyproject.toml                    # Dev deps
grep -rn "import urllib\|import subprocess" src/    # Runtime stdlib usage
```
