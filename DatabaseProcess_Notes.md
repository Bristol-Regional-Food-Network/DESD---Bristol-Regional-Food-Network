Docker Database Setup

Using the provided repository setup, the PostgreSQL database was configured inside a dedicated Docker container. The database service is defined in docker-compose.yml using the postgres:16 image.

The .env file contains the database credentials:

DB_NAME=django_db
DB_USER=django_user
DB_PASSWORD=django_password
DB_HOST=db
DB_PORT=5432

The host is set to db, which matches the service name inside Docker Compose. This allows internal container communication.

To build and start the containers:

docker compose up --build

To run in detached mode:

docker compose up -d --build

The database uses a Docker volume (postgres_data) to ensure persistence across container restarts.

Database Driver Installation

To enable Django to communicate with PostgreSQL, the required database adapter was added to requirements.txt:

psycopg2-binary

This library allows Django ORM to connect to the PostgreSQL database engine.

Connection flow:

Django ORM → psycopg2 → PostgreSQL container

Implemented Data Models

The database schema was defined in:

marketplace/models.py

The models represent the core marketplace structure:

Producer (linked to Django User)

Customer

Category

Product (Foreign Key to Producer and Category)

Inventory (One-to-One with Product)

Order

OrderItem

Payment

PayoutBatch

ProducerPayout

ProducerPayoutLine

Constraints implemented include:

Unique email for customers

Non-negative product pricing

Unique product name per producer

One-to-one relationships for inventory and payments

Foreign key constraints to enforce relational integrity

Applying Database Migrations

The initial schema was created using Django migrations located in:

marketplace/migrations/0001_initial.py

To apply migrations:

docker compose exec web python manage.py migrate

To create new migrations after modifying models:

docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

Migrations convert model definitions into SQL commands executed in PostgreSQL.

Accessing the Database

To access PostgreSQL directly inside the container:

docker compose exec db psql -U django_user -d django_db

To list all tables:

\dt

To describe a table:

\d table_name

To exit:

\q

Alternatively, Django’s database shell can be accessed using:

docker compose exec web python manage.py dbshell
Using Django Admin for CRUD Operations

The models were registered in their respective admin.py files to enable database interaction via Django Admin.

After creating a superuser:

docker compose exec web python manage.py createsuperuser

The admin interface can be accessed at:

http://localhost:8000/admin

This interface allows creation, modification, and deletion of database records for testing and validation.

Database Reset

To completely reset the database and remove stored data:

docker compose down -v
docker compose up --build

The -v flag removes the PostgreSQL volume and deletes all stored records.

Summary

The database layer has been fully containerised using PostgreSQL within Docker. Django ORM manages schema definition and migrations, while PostgreSQL enforces relational constraints and transactional integrity.

The use of Docker volumes ensures persistence, and the separation of application and database containers provides modular and scalable architecture suitable for enterprise-level development.