# Contributing to DataForge AI

First off, thank you for taking the time to contribute! Contributions from the community help make DataForge AI a robust and high-performing tool for AI data engineering.

By participating in this project, you agree to abide by our code of conduct and standard development policies.

---

## 🚀 Local Development Setup

To set up a local development workspace, follow the instructions in the main [README.md](README.md) or run the automated dev initialization script:
```powershell
./run_dev.ps1
```

Ensure you have the following prerequisites installed:
*   Python 3.11+ and [Poetry](https://python-poetry.org/)
*   Node.js 18+ and `npm`
*   PostgreSQL 15+ (optional; SQLite fallback is supported automatically)

---

## 🌿 Git Branching Conventions

We use a standard branching model to keep history clean and structured. Please prefix your branch names according to the nature of your change:

*   `feature/` — for new features, pipeline stages, or UI components (e.g. `feature/semantic-deduplication`)
*   `bugfix/` — for correcting issues or crash loops (e.g. `bugfix/crawler-timeout-handling`)
*   `docs/` — for updates to documentation, guides, or READMEs (e.g. `docs/add-api-specs`)
*   `refactor/` — for internal code cleanups or optimizations (e.g. `refactor/simhash-shingle-cache`)

---

## 🎨 Coding Standards & Quality

Maintaining a high standard of code readability and consistency is vital:

### Python Backend
*   We adhere strictly to the **PEP 8** style guide.
*   Use `black` or `autopep8` for code formatting.
*   Define clear type-hints on function and method parameters (using standard `typing` features).
*   Add docstrings to all modules, classes, and public functions.

### TypeScript / Next.js Frontend
*   We follow standard React and TypeScript patterns.
*   Do **NOT** use ad-hoc utility classes or libraries (like TailwindCSS) unless explicitly approved.
*   All styles must be managed via modern, dark-themed variables inside [globals.css](frontend/src/app/globals.css) and structural components in [page.tsx](frontend/src/app/page.tsx).

---

## 🧪 Testing Requirements

Every contribution must be verified before merging:
1.  **Backend Tests**: Run the pytest suite locally to ensure no regressions are introduced:
    ```bash
    cd backend
    poetry run python -m pytest
    ```
2.  **Frontend Compilation**: Verify that TypeScript compiles and the production static pages build correctly:
    ```bash
    cd frontend
    npm run build
    ```
3.  **New Features**: If you are adding a new pipeline stage, model, or API endpoint, you **must** supply comprehensive unit tests under `backend/tests/`.

---

## 📬 Pull Request (PR) Workflow

When you are ready to submit your code:
1.  **Sync Branch**: Fetch and merge the latest changes from `main` to prevent merge conflicts.
2.  **Verify Build**: Ensure all unit tests pass and the frontend compiles successfully.
3.  **Create PR**: Open a Pull Request targeting the `main` branch.
4.  **PR Description**: Document clearly:
    *   What problem does this change solve?
    *   What files were modified, added, or deleted?
    *   How was the change verified (e.g., test output logs or screenshots of UI modifications)?
5.  **Review**: Wait for at least one maintainer's approval and verified CI status checks before merge.
