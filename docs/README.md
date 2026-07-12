# Fabricium Documentation

Shared Hermes plugin infrastructure — build plugins in 5 minutes. Python library, zero runtime dependencies.

## I want to...

| I want to... | Read... |
|-------------|---------|
| Understand the system design | [Architecture](architecture.md) |
| See the technology inventory | [Tech Stack](tech-stack.md) |
| Find where code lives | [Project Structure](project-structure.md) |
| Know code conventions | [Conventions](conventions.md) |
| Browse the public API | [API Reference](api-reference.md) |
| Set up the project from scratch | [Setup](setup.md) |
| Run or write tests | [Testing](testing.md) |
| Follow step-by-step recipes | [Workflows](workflows.md) |
| Understand the state/data layer | [Data Models](data-models.md) |

## Modules

| Module | Description |
|--------|-------------|
| [Core](modules/core.md) | `HermesPlugin` — plugin lifecycle manager (setup/status/update) |
| [Skills](modules/skills.md) | Bundled skill discovery, installation, stale cleanup |
| [State](modules/state.md) | JSON state persistence (`~/.hermes/<plugin>_state.json`) |
| [Git Utils](modules/git-utils.md) | Git subprocess wrappers for self-update |
| [Testing](modules/testing.md) | Docker-based integration test environment |
| [Evals](modules/evals.md) | LLM-as-Judge skill evaluation framework |

## Document Index

| File | Description |
|------|-------------|
| [tech-stack.md](tech-stack.md) | Languages, frameworks, tools with versions |
| [project-structure.md](project-structure.md) | Directory map — where code lives |
| [architecture.md](architecture.md) | C4 diagrams, data flows, architectural decisions |
| [conventions.md](conventions.md) | Naming, imports, error handling, state management |
| [api-reference.md](api-reference.md) | Full Python API surface summary |
| [data-models.md](data-models.md) | State file schema and lifecycle |
| [setup.md](setup.md) | Install, verify, env vars, Docker |
| [testing.md](testing.md) | Test framework, layout, fixtures, commands |
| [workflows.md](workflows.md) | Release, add API, eval pipeline, debug, build plugin |
| [modules/core.md](modules/core.md) | `HermesPlugin` deep dive |
| [modules/skills.md](modules/skills.md) | Skill lifecycle deep dive |
| [modules/state.md](modules/state.md) | State persistence deep dive |
| [modules/git-utils.md](modules/git-utils.md) | Git wrappers deep dive |
| [modules/testing.md](modules/testing.md) | Test harness deep dive |
| [modules/evals.md](modules/evals.md) | Eval framework deep dive |

See also: [Project README](../README.md) for user-facing documentation and quick start.

## How to Update

- New doc file? → Add to document index + "I want to..." table.
- Doc file removed? → Remove from both index tables.
- Module added? → Add row to modules table + create `modules/<name>.md`.
- Architecture changed? → Update `architecture.md` diagrams + decisions table.

## Find It Fast

```bash
ls docs/                                   # All doc files
grep -rn "\[.*\](.*\.md)" docs/           # All cross-references
```
