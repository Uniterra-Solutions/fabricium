# Module: Git Utils (`fabricium.git_utils`)

**Purpose:** Git subprocess wrappers for plugin self-update. All functions accept optional `repo_path` (defaults to CWD).

**File:** `src/fabricium/git_utils.py`

## Public API

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `is_git_repo(repo_path?)` | `(str?) -> bool` | — | Check if path is inside a git worktree |
| `get_head_hash(repo_path?)` | `(str?) -> str` | — | Full SHA of HEAD |
| `get_diff(start_hash, end="HEAD", repo_path?)` | `(str, str, str?) -> str` | — | Git diff between two refs |
| `get_diff_stat(start_hash, end="HEAD", repo_path?)` | `(str, str, str?) -> list[dict]` | `[{"path", "additions", "deletions"}]` | Changed files with line counts |
| `get_remote_url(repo_path?)` | `(str?) -> str` | — | Origin URL, empty string if none |
| `get_default_branch(repo_path?)` | `(str?) -> str` | — | Remote HEAD ref name, falls back to `"main"` |
| `fetch_remote(repo_path?)` | `(str?) -> FetchResult` | `{"success": bool, "message": str}` | Fetch from origin (30s timeout) |
| `get_remote_head(repo_path?)` | `(str?) -> str\|None` | — | SHA of `origin/<default_branch>` |
| `get_local_head(repo_path?, ref?)` | `(str?, str?) -> str\|None` | — | SHA of a local ref |
| `get_ahead_behind(repo_path?, base?, remote_ref?)` | `(str?, str?, str?) -> AheadBehind` | `{"ahead": int, "behind": int, "remote_head": ...}` | Ahead/behind counts |
| `is_ancestor(ancestor, descendant, repo_path?)` | `(str, str, str?) -> bool` | — | True if ancestor==descendant or ancestor is ancestor |
| `pull_branch(repo_path?)` | `(str?) -> PullResult` | `{"success", "message", "before", "after"}` | Fast-forward pull (60s timeout) |
| `stage_all(repo_path?)` | `(str?) -> None` | — | `git add -A` |
| `commit(message, repo_path?)` | `(str, str?) -> CommitResult` | `{"success", "message"}` | Commit staged changes |

All functions use `_git_cmd(repo_path)` which builds `["git", "-C", "<resolved_path>"]` — absolute path resolution avoids CWD ambiguity.

## TypedDicts

| Type | Fields |
|------|--------|
| `FetchResult` | `success: bool`, `message: str` |
| `AheadBehind` | `ahead: int`, `behind: int`, `remote_head: str \| None` |
| `PullResult` | `success: bool`, `message: str`, `before: str \| None`, `after: str \| None` |
| `CommitResult` | `success: bool`, `message: str` |

## Dependencies

**Inbound:** `fabricium/__init__.py` (`HermesPlugin._update_check`, `_update_pull`).

**Outbound:** None (stdlib only: `subprocess`, `pathlib`, `typing`).

## Patterns & Gotchas

- **All operations return structured results** — no functions raise exceptions. Callers check `.success` fields.
- **`fetch_remote` timeout** (`src/fabricium/git_utils.py:125`): 30-second timeout prevents hanging on unreachable remotes.
- **`pull_branch` fast-forward only** (`src/fabricium/git_utils.py:218`): `--ff-only` prevents merge commits. Non-FF returns `success: False`.
- **`get_default_branch` fallback** (`src/fabricium/git_utils.py:114`): Returns `"main"` if `origin/HEAD` is not a symbolic ref (common in older repos).
- **`_git_cmd` resolves paths** (`src/fabricium/git_utils.py:41`): `Path(repo_path or ".").resolve()` — relative paths are always resolved before passing to `git -C`.

## See Also

- [Core Module](core.md) — update command usage of git utils
- [Architecture](../architecture.md#data-flow-plugin-update) — update data flow

## How to Update

- New git operation? → Add function + row to API table + TypedDict if needed.
- Timeout changed? → Update function docs.
- New caller? → Update inbound dependencies.

## Find It Fast

```bash
grep -n "def " src/fabricium/git_utils.py                     # All functions
grep -rn "git_utils\." src/fabricium/__init__.py              # All callers in core
```
