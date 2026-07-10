# DataForge AI

**DataForge AI** is a production-quality, high-throughput AI Data Engineering Pipeline designed to collect, clean, normalize, deduplicate, analyze, and export datasets suitable for AI training and evaluation.

This repository implements the complete Phase 1 Foundation and Monorepo Architecture.

---

## 🏗️ Project Architecture

We use a modular architecture separated into frontend, backend, and configuration roots:

```
DataForge-AI/
├── .env.example                 # Example root environment file
├── .gitignore                   # Global ignore file (updated)
├── docker-compose.yml           # Multi-container orchestration
├── README.md                    # Architecture and developer guide
├── run_dev.ps1                  # Local developer helper script
├── backend/                     # FastAPI backend application
│   ├── app/
│   │   ├── api/                 # API Routes & Versioning
│   │   │   ├── router.py        # Main API Router
│   │   │   └── v1/
│   │   │       ├── router.py    # V1 Router
│   │   │       └── endpoints/
│   │   │           └── health.py # Health check endpoint
│   │   ├── core/                # System config, database, logging
│   │   │   ├── config.py        # Settings management via Pydantic
│   │   │   ├── database.py      # SQLAlchemy DB session setup
│   │   │   └── logging.py       # Custom logger config
│   │   └── main.py              # Application entrypoint
│   ├── migrations/              # Alembic migrations folder
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/                   # Pytest suite
│   │   ├── conftest.py
│   │   └── test_health.py
│   ├── alembic.ini              # Alembic config
│   ├── Dockerfile               # Backend production Dockerfile
│   └── pyproject.toml           # Poetry backend dependencies
└── frontend/                    # Next.js frontend application
    ├── src/
    │   ├── app/                 # Next.js App Router
    │   │   ├── layout.tsx       # Root layout
    │   │   ├── page.tsx         # Dashboard landing page
    │   │   └── health/
    │   │       └── page.tsx     # Extended health dashboard
    │   └── styles/
    │       └── globals.css      # Vanilla CSS theme and styling variables
    ├── package.json             # NPM frontend dependencies
    ├── Dockerfile               # Frontend production Dockerfile
    └── ...
```

### Key Configuration Files
*   **Root Configs**: [docker-compose.yml](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/docker-compose.yml) | [.env.example](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/.env.example) | [.gitignore](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/.gitignore)
*   **Backend Configs**: [pyproject.toml](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/backend/pyproject.toml) | [Dockerfile](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/backend/Dockerfile) | [alembic.ini](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/backend/alembic.ini)
*   **Frontend Configs**: [package.json](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/frontend/package.json) | [Dockerfile](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/frontend/Dockerfile)

---

## 🛠️ Tech Stack & Tooling

1.  **FastAPI (Python Backend)**: Fast, type-safe API framework.
2.  **Next.js (TypeScript Frontend)**: Modern App Router layout, styled exclusively using premium dark-theme **Vanilla CSS**.
3.  **SQLAlchemy**: Asynchronous Object Relational Mapping (ORM) connecting to PostgreSQL.
4.  **Alembic**: Asynchronous database schema migrations management.
5.  **Poetry**: Deterministic dependency resolution and package management.
6.  **Docker & Docker Compose**: Complete containerized deployment orchestration.

---

## 🐋 Docker Compose Orchestration

For fully containerized execution, we define three services in [docker-compose.yml](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/docker-compose.yml):
*   `db`: PostgreSQL 15 database service.
*   `backend`: FastAPI server mounting code with live reloading and auto-migrations.
*   `frontend`: Next.js web application server.

### Steps to Install Docker Desktop on Windows
If Docker is not currently installed or configured on your system, please execute the following steps:
1.  **Enable CPU Virtualization**: Ensure virtualization is enabled in your BIOS/UEFI settings (typically enabled by default on modern machines).
2.  **Install WSL 2**: Open PowerShell as Administrator and run:
    ```powershell
    wsl --install
    ```
    Restart your machine when prompted to finish the WSL installation.
3.  **Download Docker**: Download the installer from the official [Docker Desktop page](https://www.docker.com/products/docker-desktop/).
4.  **Run Installer**: Execute the installer, ensuring the option **Use WSL 2 instead of Hyper-V** remains checked.
5.  **Launch Docker Desktop**: Open Docker Desktop and accept the terms to start the Docker daemon.

### Starting Docker Compose
Once Docker is active, run:
```bash
docker compose up --build
```
Access the services at:
*   Frontend: `http://localhost:3000`
*   Backend API: `http://localhost:8000`
*   Interactive API Docs: `http://localhost:8000/docs`

---

## 💻 Local Development Setup (Without Docker)

You can run the entire pipeline locally without Docker. If a local PostgreSQL server is not available, the backend automatically falls back to an SQLite database file (`./dataforge.db`) dynamically.

### 🚀 Quick Start Script
We have provided a custom PowerShell script [run_dev.ps1](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/run_dev.ps1) that automatically configures active settings and boots both servers in separate, named console windows:
```powershell
./run_dev.ps1
```

### Manual Service Startup

#### 1. Setup Backend:
1.  Navigate to the `backend/` folder.
2.  Install dependencies:
    ```bash
    python -m poetry install
    ```
3.  Start FastAPI dev server:
    ```bash
    python -m poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    ```

#### 2. Setup Frontend:
1.  Navigate to the `frontend/` folder.
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start Next.js dev server:
    ```bash
    npm run dev
    ```

---

## 💾 Database Schema Migrations (Alembic)

Alembic is configured dynamically via [migrations/env.py](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/backend/migrations/env.py) to read database configuration from the application settings.

To create an autogenerated migration revision:
```bash
python -m poetry run alembic revision --autogenerate -m "description_here"
```

To execute migrations to head:
```bash
python -m poetry run alembic upgrade head
```

---

## 🧪 Testing & Verification

We use `pytest` for backend unit testing. Tests automatically use an isolated, in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) to ensure speed and independence from external servers.

Run tests:
```bash
python -m poetry run python -m pytest
```
Test cases cover welcome routers, root health checks, versioned health checks, and database connection checks. See [test_health.py](file:///c:/Users/bradr/OneDrive/Documents/GitHub/DataForge-AI/backend/tests/test_health.py).
