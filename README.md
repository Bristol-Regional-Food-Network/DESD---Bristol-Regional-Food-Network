# Bristol Regional Food Network Platform  
DESD – Distributed & Enterprise Software Development  

This project is a Django-based web application containerised using Docker.  
It uses PostgreSQL as the database and runs in a multi-container environment.

---

#  Prerequisites

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

# Running the Application with Docker

To ensure the application runs consistently across different environments, the system is containerised using Docker. Docker packages the application together with all required dependencies, allowing the project to run in the same way regardless of the host operating system.

The application uses Docker Compose to orchestrate multiple services required for the system. In this project two containers are defined:

**Web container** – runs the Django application.

**Database container** – runs a PostgreSQL database instance used by the application.

**Docker Compose** automatically creates a shared network between these services so the Django application can communicate with the *PostgreSQL* database using the service name defined in the configuration.

# Building and Starting the Containers

After cloning the repository and navigating to the project directory, the application can be built and started using the following command:

      docker compose up --build

This command performs several actions:

- Builds the Docker image for the Django application using the provided Dockerfile.

- Pulls the PostgreSQL database image if it is not already available locally.

- Starts both the database and web containers.

- Applies Django database migrations automatically when the web container starts.

*Once the containers are running successfully, the Django development server will be available at: http://localhost:8000*

# Stopping the Containers

To stop the running containers, the following command can be used:

      docker compose down

If it is necessary to completely remove the containers and associated database volume, the following command can be used:

      docker compose down -v

This removes the persistent database volume and allows the system to start again with a fresh database state.

# Environment Configuration

Environment variables used by the application are defined in the **.env** file. These variables include the database connection settings and the Django secret key required for the application to run.

**Docker Compose** automatically loads these variables when starting the containers, ensuring that the **Django** application can connect to the **PostgreSQL** database correctly within the **Docker** environment.