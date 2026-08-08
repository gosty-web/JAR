# Coding Standards

This is a production-grade system. Code quality, testability, and clear boundaries are mandatory.

## 1. General Principles
- **No magic strings**: Use Enums or constants for event names, states (e.g., `OrbState.THINKING`), and subsystem identifiers.
- **Fail loud and early**: If a subsystem cannot initialize, crash the process with a clear log. Do not fail silently.
- **Strict Typing**: Use type hints in Python and strict TypeScript in the frontend. 

## 2. Python Standards (Core)
- **Formatting**: `black` (line length 100).
- **Linting**: `flake8` and `mypy` (strict mode).
- **Style Guide**: PEP 8.
- **Dependencies**: Managed via `requirements.txt` or `poetry`. Pin all dependencies.
- **Documentation**: Use Google-style docstrings for all classes and functions.
- **Async**: Use `asyncio` for non-blocking I/O. Never use blocking calls in the main event loop.

## 3. Frontend Standards (Electron/React)
- **Formatting**: `prettier`.
- **Linting**: `eslint` with strict TypeScript rules.
- **Components**: Functional components only. No class components.
- **Styling**: Tailwind CSS. Stick to the design tokens (glassmorphism rules).

## 4. Git & Commits
- Follow [Conventional Commits](https://www.conventionalcommits.org/).
  - `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- PRs must pass all CI checks before merge.

## 5. Testing Requirements
- **Core (Python)**: `pytest`. Every skill must have a unit test testing both success and error-recovery paths.
- **Frontend (TS)**: `jest` and React Testing Library. 

## 6. Code Review Checklist
- [ ] Are failure modes handled and logged?
- [ ] Is the action properly verification-gated?
- [ ] Does this touch the World-State Tracker correctly?
- [ ] Are secrets/keys kept out of logs and source?
