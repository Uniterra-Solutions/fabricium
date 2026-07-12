# Module: Evals (`fabricium.evals`)

**Purpose:** LLM-as-Judge skill evaluation framework. Docker-based infrastructure for measuring how much a skill improves agent output quality. Follows SkillsBench methodology: identical prompts, universal rubrics, output-quality deltas.

**Files:** `src/fabricium/evals/harness.py`, `judge.py`, `config.py`, `tasks.py`, `rubrics.py`, `runner.py`, `proxy.py`

## Public API

| Class/Function | Description |
|----------------|-------------|
| `SkillEvalHarness` | Docker orchestration: containers, profiles, workspaces, agent execution, judging |
| `JudgeClient` | LLM-as-Judge with cross-provider support (Anthropic, OpenAI-compatible) |
| `EvalConfig` | Environment-variable-driven configuration |
| `ModelConfig` | Provider + model + credential + endpoint |
| `EvalTask` | Task definition: prompts, seed files, verify commands |
| `RubricSpec` / `RubricDimension` / `ScoringBand` | Rubric building blocks |
| `JudgePrompt` | Customizable judge prompt template |
| `JudgeReport` | Parsed judge verdict: dimensions, scores, weighted total |
| `AgentRunResult` | Complete output from one agent invocation |
| `EvalReport` | Top-level report: results, verdicts, skill lift |
| `calibrate(human_labels, judge_reports)` | Judge-human agreement metrics (Cohen's κ, Spearman ρ) |
| `load_config()` | Build `EvalConfig` from environment variables |

## CLI Entry Point

```bash
python -m fabricium.evals.runner
```

Requires env vars: `EVAL_CANDIDATE_PROVIDER`, `EVAL_CANDIDATE_MODEL`, `EVAL_JUDGE_PROVIDER`, `EVAL_JUDGE_MODEL`, `EVAL_JOVALTUS_PLUGIN_DIR`, plus API keys.

## Eval Pipeline (per task)

```
1. Start Docker container (nousresearch/hermes-agent:latest)
2. Copy Jovaltus plugin → /opt/data/plugins/jovaltus
3. Create bare profile (no skills)
4. Create jovaltus-agent profile (hermes jovaltus setup)
5. For each profile, for each run:
   a. Init git workspace with seed files
   b. Run: hermes -p <profile> chat -q "<prompt>"
   c. Capture: exit code, stdout, file tree, file contents, build results, git commits
6. Judge last run of each profile with JudgeClient
7. Compute skill lift: skill_score - bare_score
8. Write report JSON to eval_results/
```

## Judge Configuration

### Default Prompt (`judge.py:75-135`)

- System: expert code reviewer protocol with chain-of-thought
- User template: `{task_prompt}`, `{file_tree}`, `{file_contents}`, `{build_results}`, `{trace_summary}`, `{rubric_json}`
- Forces reasoning before numeric scores

### Provider Support

| Provider | API | Auth |
|----------|-----|------|
| Anthropic | `https://api.anthropic.com/v1/messages` | `x-api-key` header |
| OpenAI-compatible | `{base}/v1/chat/completions` | `Bearer` token |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | `Bearer` token |
| OpenRouter | `https://openrouter.ai/api/v1/chat/completions` | `Bearer` token |
| Google | Gemini via OpenAI-compatible endpoint | `Bearer` token |
| Groq | `https://api.groq.com/openai/v1/chat/completions` | `Bearer` token |
| xAI | `https://api.x.ai/v1/chat/completions` | `Bearer` token |
| Custom | Via `api_base` env var or `custom:<name>` provider ref | `Bearer` token |

## Reasoning-Model SSE Proxy (`proxy.py`)

DeepSeek V4 outputs `reasoning_content` before `content`. During streaming, Hermes sees `content: null` and fails. The proxy:

- Patches `"content": null` → `"content": ""` in SSE chunks
- For non-streaming: falls back to `reasoning_content` if `content` is empty
- Runs as `python3 proxy.py <API_KEY> <UPSTREAM_URL> [PORT]`

## Dependencies

**Inbound:** `fabricium.evals.runner` (CLI), external eval scripts.

**Outbound:**
- Docker CLI (`subprocess.run(["docker", ...])`)
- `urllib.request` for HTTP judge API calls
- No SDK dependencies — pure stdlib

## Patterns & Gotchas

- **Provider cross-check** (`config.py:183-190`): Warns if judge and candidate use same provider (self-preference bias).
- **Custom provider auto-config** (`harness.py:426-439`): Non-standard providers auto-wrapped as `custom:<name>` with `custom_providers` YAML block.
- **API base normalisation** (`harness.py:466-468`): Auto-appends `/v1` if not present.
- **Workspace ownership** (`harness.py:530`): `chown -R hermes:hermes` after workspace init — Docker exec runs as root, Hermes agent runs as `hermes` user.
- **Position randomisation** (`judge.py:219`): Judge evaluates bare/skill in random order to avoid position bias.
- **Non-JSON fallback** (`judge.py:383-398`): If judge returns non-JSON, all dimensions scored 0 with warning.
- **DeepSeek V4 `reasoning_content` fallback** (`judge.py:279`): `msg.get("content") or msg.get("reasoning_content", "")` — handles thinking-mode responses.

## See Also

- [Testing Module](testing.md) — similar Docker patterns
- [Architecture](../architecture.md#data-flow-eval-pipeline)

## How to Update

- New judge provider? → Add to provider support table + URL map in `_resolve_base_url()`.
- New eval config option? → Add to `EvalConfig` dataclass + `load_config()`.
- Runner behaviour changed? → Update eval pipeline section.

## Find It Fast

```bash
grep -n "class " src/fabricium/evals/harness.py      # All harness classes
grep -n "def " src/fabricium/evals/judge.py           # All judge methods
grep -n "EVAL_" src/fabricium/evals/config.py         # All env var names
python -m fabricium.evals.runner --help 2>/dev/null || echo "See runner.py:main()"
```
