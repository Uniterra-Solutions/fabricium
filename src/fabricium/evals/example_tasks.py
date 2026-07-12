"""Example tasks for Jovaltus skill evaluation.

This file demonstrates how a caller (e.g. the Jovaltus project) defines
their own tasks.  Copy this into your project, customise, and pass the
resulting :class:`EvalTask` list to :class:`SkillEvalHarness`.

To use these exact tasks::

    from fabricium.evals.example_tasks import JOVALTUS_TASKS
    harness.run(JOVALTUS_TASKS, rubric)
"""

from __future__ import annotations

import textwrap

from .tasks import EvalTask

# ── Seed files ──────────────────────────────────────────────────────

_PYPROJECT = """\
[project]
name = "todo-backend"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
    "passlib[bcrypt]>=1.7",
    "pytest>=8",
    "httpx>=0.28",
]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

_PACKAGE_JSON = """\
{
  "name": "landing-page",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }
}
"""

_FS_BACKEND_PYPROJECT = """\
[project]
name = "todo-backend"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115", "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0", "pydantic>=2.0",
    "pytest>=8", "httpx>=0.28",
]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

# ── Prompt templates ─────────────────────────────────────────────────

_PY_NATURAL = textwrap.dedent("""\
    Build a FastAPI backend service with the following requirements:

    ## Functional Requirements
    1. User registration and login API endpoints (use SQLite, hash passwords)
    2. A CRUD task management endpoint (tasks must be associated with users)
    3. Use Pydantic for input validation on all endpoints
    4. Proper HTTP error responses (404, 422, 401)

    ## Edge Cases to Handle
    - Duplicate email registration → 409 Conflict
    - Wrong password on login → 401
    - Operating on another user's task → 403
    - Empty/invalid request bodies → 422
    - Non-existent resource IDs → 404

    ## Testing Requirements
    Write pytest tests covering:
    - Happy-path for every endpoint
    - Error cases for each edge case listed above
    - At least 15 tests total

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. one commit for models, one for auth, one for routes, one for tests
    - No dead code, no unused imports
    - All functions have type annotations

    Work in /workspace/python-backend/.
    When done, `uv run pytest` must pass.""")

_PY_EXPLICIT = textwrap.dedent("""\
    Build a FastAPI backend service with the following requirements:

    ## Functional Requirements
    1. User registration and login API endpoints (use SQLite, hash passwords)
    2. A CRUD task management endpoint (tasks must be associated with users)
    3. Use Pydantic for input validation on all endpoints
    4. Proper HTTP error responses (404, 422, 401)

    ## Edge Cases to Handle
    - Duplicate email registration → 409 Conflict
    - Wrong password on login → 401
    - Operating on another user's task → 403
    - Empty/invalid request bodies → 422
    - Non-existent resource IDs → 404

    ## Testing Requirements
    Write pytest tests covering:
    - Happy-path for every endpoint
    - Error cases for each edge case listed above
    - At least 15 tests total

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. one commit for models, one for auth, one for routes, one for tests
    - No dead code, no unused imports
    - All functions have type annotations

    Work in /workspace/python-backend/.
    When done, `uv run pytest` must pass.""")

_TS_NATURAL = textwrap.dedent("""\
    Build a responsive SaaS landing page using
    Vite + React + TypeScript + Tailwind CSS:

    ## Functional Requirements
    1. Fixed top navigation bar with logo and nav links
    2. Hero section with title, subtitle, and CTA button
    3. Features section with 3 feature cards — responsive grid
       (3 cols desktop, 2 tablet, 1 mobile)
    4. Footer with links and copyright
    5. Dark/light mode toggle using Tailwind dark: classes

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. one commit for layout, one for responsive, one for dark mode
    - No dead code, no unused imports
    - All components have TypeScript prop types

    Work in /workspace/typescript-frontend/.
    When done, `npm run build` must succeed.""")

_TS_EXPLICIT = textwrap.dedent("""\
    Build a responsive SaaS landing page using
    Vite + React + TypeScript + Tailwind CSS:

    ## Functional Requirements
    1. Fixed top navigation bar with logo and nav links
    2. Hero section with title, subtitle, and CTA button
    3. Features section with 3 feature cards — responsive grid
       (3 cols desktop, 2 tablet, 1 mobile)
    4. Footer with links and copyright
    5. Dark/light mode toggle using Tailwind dark: classes

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. one commit for layout, one for responsive, one for dark mode
    - No dead code, no unused imports
    - All components have TypeScript prop types

    Work in /workspace/typescript-frontend/.
    When done, `npm run build` must succeed.""")

_FS_NATURAL = textwrap.dedent("""\
    Build a complete Todo List application:

    Backend (FastAPI + SQLite, in backend/):
    1. POST /todos — create a todo ({title, completed: false})
    2. GET /todos — list all todos
    3. PUT /todos/{id} — update a todo
    4. DELETE /todos/{id} — delete a todo
    5. GET /todos?completed=true|false — filter

    ## Edge Cases to Handle
    - Empty title on create → 422
    - Non-existent todo ID on update/delete → 404
    - Invalid completed filter value → 422

    Frontend (React + TypeScript + Tailwind, in frontend/):
    1. Display todo list (fetched from backend API)
    2. Input + button to add new todos
    3. Checkbox to toggle completion
    4. Delete button per todo
    5. Filter buttons (All / Active / Completed)

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. backend in one commit, frontend in another, integration in a third
    - Write pytest tests for backend edge cases (at least 10 tests)
    - No dead code, no unused imports

    Work in /workspace/fullstack-todo/.
    Backend: `uv run pytest` must pass.
    Frontend: `npm run build` must succeed.""")

_FS_EXPLICIT = textwrap.dedent("""\
    Build a complete Todo List application:

    Backend (FastAPI + SQLite, in backend/):
    1. POST /todos — create a todo ({title, completed: false})
    2. GET /todos — list all todos
    3. PUT /todos/{id} — update a todo
    4. DELETE /todos/{id} — delete a todo
    5. GET /todos?completed=true|false — filter

    ## Edge Cases to Handle
    - Empty title on create → 422
    - Non-existent todo ID on update/delete → 404
    - Invalid completed filter value → 422

    Frontend (React + TypeScript + Tailwind, in frontend/):
    1. Display todo list (fetched from backend API)
    2. Input + button to add new todos
    3. Checkbox to toggle completion
    4. Delete button per todo
    5. Filter buttons (All / Active / Completed)

    ## Quality Requirements
    - Commit your work in logical stages (not one giant commit)
       e.g. backend in one commit, frontend in another, integration in a third
    - Write pytest tests for backend edge cases (at least 10 tests)
    - No dead code, no unused imports

    Work in /workspace/fullstack-todo/.
    Backend: `uv run pytest` must pass.
    Frontend: `npm run build` must succeed.""")

# ── Task definitions ─────────────────────────────────────────────────

TASK_PYTHON_BACKEND = EvalTask(
    id="python-backend",
    name="Python Backend + Database",
    description="FastAPI CRUD backend with SQLite, auth, and pytest",
    workspace_subdir="python-backend",
    natural_prompt=_PY_NATURAL,
    explicit_prompt=_PY_EXPLICIT,
    seed_files={"pyproject.toml": _PYPROJECT},
    verify_commands=[
        ("pytest", "cd /workspace/python-backend && uv run pytest -v"),
        ("main.py", "test -f /workspace/python-backend/main.py"),
    ],
)

TASK_TYPESCRIPT_FRONTEND = EvalTask(
    id="typescript-frontend",
    name="TypeScript Frontend Web Design",
    description="Responsive React+TS+Tailwind landing page",
    workspace_subdir="typescript-frontend",
    natural_prompt=_TS_NATURAL,
    explicit_prompt=_TS_EXPLICIT,
    seed_files={"package.json": _PACKAGE_JSON},
    verify_commands=[
        ("build", "cd /workspace/typescript-frontend && npm run build"),
        ("App.tsx", "test -f /workspace/typescript-frontend/src/App.tsx"),
    ],
)

TASK_FULLSTACK_TODO = EvalTask(
    id="fullstack-todo",
    name="Fullstack Todo List",
    description="FastAPI + React integrated todo app",
    workspace_subdir="fullstack-todo",
    natural_prompt=_FS_NATURAL,
    explicit_prompt=_FS_EXPLICIT,
    seed_files={
        "backend/pyproject.toml": _FS_BACKEND_PYPROJECT,
        "frontend/package.json": _PACKAGE_JSON,
    },
    verify_commands=[
        ("backend tests", "cd /workspace/fullstack-todo/backend && uv run pytest -v"),
        ("frontend build", "cd /workspace/fullstack-todo/frontend && npm run build"),
    ],
)

JOVALTUS_TASKS: list[EvalTask] = [
    TASK_PYTHON_BACKEND,
    TASK_TYPESCRIPT_FRONTEND,
    TASK_FULLSTACK_TODO,
]
