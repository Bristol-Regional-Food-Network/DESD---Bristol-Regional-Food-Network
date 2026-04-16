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

---

# Docker Commands
## Start/Stop
### Start containers (foreground)
```bash
docker compose up
```

### Start containers (background)
```bash
docker compose up -d
```

### Stop containers (foreground)
Press CTRL + C

### Stop containers (background)
```bash
docker compose down
```

## Migrations
### When to run migrations
- New model created  
- Field added/removed/changed  
- New app with models  
- Foreign key added  
- Model renamed  

### Make Migrations
```bash
docker compose exec web python manage.py makemigrations
```

### Apply Migrations
```bash
docker compose exec web python manage.py migrate
```