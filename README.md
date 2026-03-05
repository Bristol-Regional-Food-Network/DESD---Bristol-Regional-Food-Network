# 🌱 Bristol Regional Food Network Platform  
DESD – Distributed & Enterprise Software Development  

This project is a Django-based web application containerised using Docker.  
It uses PostgreSQL as the database and runs in a multi-container environment.

---

# 📦 Prerequisites

Before running the project, install the following:

- **Git**  
  https://git-scm.com/

- **Docker Desktop** (Windows/Mac)  
  https://www.docker.com/products/docker-desktop/

After installing Docker Desktop:
- Make sure Docker Desktop is **running**
- Windows users: ensure **WSL 2 integration** is enabled

To verify installation:

```bash
docker --version
docker compose version
```

# Environment Setup

```bash
copy .env.example .env
```

# Project structure 

``` bash 

.
├── app/
├── web_project/
├── docker/
│   └── Dockerfile
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── docker-compose.yml
├── .env.example
├── manage.py
└── README.md
```
## Session configuration

Control login session behaviour via environment variables (all optional; defaults shown):

- `SESSION_COOKIE_AGE` (default `1209600` seconds / 14 days)
- `SESSION_EXPIRE_AT_BROWSER_CLOSE` (`0` keep session cookie, `1` drop on browser close)
- `SESSION_SAVE_EVERY_REQUEST` (`0` default, `1` refresh expiry on each request)
- `SESSION_COOKIE_SECURE` (`1` in production behind HTTPS)
- `SESSION_COOKIE_SAMESITE` (`Lax` recommended; use `None` only when required for cross-site)
- `SECURE_SSL_REDIRECT` (`1` to force HTTPS; disable locally)
- `CSRF_COOKIE_SECURE`/`CSRF_COOKIE_SAMESITE` follow the session cookie settings automatically