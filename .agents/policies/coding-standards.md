# Policy: Coding Standards & Engineering Practices

## 1. Python Standards (Backend & Agent Runtime)
1. **Python Version**: Python 3.11+.
2. **Formatting & Style**:
   - Formatter: `black` with 100-character line length.
   - Linter: `ruff` (errors, pyflakes, bugbear, isort).
   - Type Checking: `mypy` with type annotations required on all public functions, methods, and classes.
3. **Async / Concurrency**:
   - Use `async/await` for I/O-bound operations (FastAPI route handlers, database queries via `asyncpg`, HTTP calls via `httpx`).
   - Do not call blocking synchronization primitives (`time.sleep`) inside async contexts; use `asyncio.sleep`.
4. **Data Modeling**:
   - Use Pydantic v2 `BaseModel` for external schemas and API input/output validation.
   - Use SQLAlchemy 2.0 `Mapped[...]` and `mapped_column(...)` declarative ORM syntax.
5. **Error Handling**:
   - Inherit from custom base exceptions in `backend/src/gitpulse/common/exceptions.py`.
   - Never suppress exceptions with bare `except: pass`.

## 2. TypeScript & React Standards (Frontend)
1. **Strict TypeScript**:
   - `strict: true` in `tsconfig.json`.
   - Explicit return types on service calls and exported hooks.
   - Prohibit the `any` type; use `unknown` with type narrowing or generic parameters.
2. **React 18+ Idioms**:
   - Use functional components with typed props interfaces (`interface ComponentProps { ... }`).
   - Keep business logic in custom hooks (`useRepoVelocity.ts`) and presentational UI pure.
   - Maintain stable hook dependency arrays; never disable `react-hooks/exhaustive-deps` without architectural review.
3. **Styling & Assets**:
   - CSS Modules or utility classes adhering to design tokens.
   - All interactive elements must have keyboard accessibility and descriptive labels.

## 3. Data Platform & SQL Standards
1. **Naming Conventions**:
   - Tables: Plural snake_case (`github_repositories`, `commit_events`).
   - Views & Marts: Standard dbt prefixes:
     - `stg_` for staging views
     - `int_` for intermediate models
     - `fct_` for fact tables
     - `dim_` for dimension tables
2. **SQL Formatting**:
   - Capitalized SQL keywords (`SELECT`, `FROM`, `WHERE`, `GROUP BY`).
   - Commas placed at the beginning or end consistently.
   - Avoid `SELECT *`; always explicitly project columns.
