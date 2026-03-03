Database Design and Implementation
1. Overview

This project uses PostgreSQL as the relational database management system and Django ORM to define and manage the schema. The database runs inside a dedicated Docker container and communicates with the Django application container through Docker Compose.

The goal of this setup is to separate application logic from data storage while ensuring portability, persistence, and structured relational integrity.

2. Database Technology and Libraries
Database System

PostgreSQL 16 (Docker container)

ORM

Django ORM

Required Python Library

The PostgreSQL driver used by Django is included in requirements.txt:

psycopg2-binary

This library enables communication between:

Django ORM → psycopg2 → PostgreSQL

Without this dependency, Django cannot connect to the PostgreSQL database.

3. Environment Configuration

Database credentials are stored in the .env file:

DB_NAME=django_db
DB_USER=django_user
DB_PASSWORD=django_password
DB_HOST=db
DB_PORT=5432

Important detail:

DB_HOST=db works because db is the service name defined in docker-compose.yml. Docker automatically creates internal networking between containers.

In settings.py, Django reads these values:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}
4. Docker Database Setup

The database service is defined in docker-compose.yml using:

Image: postgres:16

Port mapping: 5432:5432

Persistent volume: postgres_data

The volume ensures that data remains stored even if containers are restarted.

5. Running the Database (Execution Phases)
Phase 1 – Build and Start Containers
docker compose up --build

This command:

Builds the Django image

Starts the PostgreSQL container

Waits for the database to be ready

Applies migrations

Starts the Django development server

To run in background:

docker compose up -d --build
Phase 2 – Apply Migrations

If migrations are not applied automatically:

docker compose exec web python manage.py migrate

To create new migrations after editing models:

docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

Migrations convert Django model definitions into SQL statements executed in PostgreSQL.

Phase 3 – Access the Database

To access PostgreSQL directly:

docker compose exec db psql -U django_user -d django_db

List tables:

\dt

Describe a table:

\d table_name

Exit:

\q

Alternatively, access via Django:

docker compose exec web python manage.py dbshell
Phase 4 – Reset the Database

To completely remove all stored data:

docker compose down -v
docker compose up --build

The -v flag removes the Docker volume and deletes all database data.

6. Database Schema Structure

The schema is defined in:

marketplace/models.py

Initial migration:

marketplace/migrations/0001_initial.py
Core Entities

Producer

Linked to Django User model

Stores producer information

Customer

Stores buyer details

Email is unique

Category

Product classification

Unique name

Product

Linked to Producer (Foreign Key)

Linked to Category (Foreign Key)

Stores pricing, description, flags

Unique product name per producer

Price must be non-negative

Inventory

One-to-one relationship with Product

Tracks stock and availability dates

Orders and Payments

Order

Linked to Customer

Stores totals, status, timestamps

OrderItem

Linked to Order

Linked to Product

Stores purchase-time pricing

Payment

One-to-one relationship with Order

Stores provider and payment status

This design preserves transactional integrity and historical pricing.

Financial Payout System

PayoutBatch

Defines payout periods

ProducerPayout

Linked to Producer and PayoutBatch

Stores commission and net payable

ProducerPayoutLine

Linked to OrderItem

Ensures payout traceability

7. Data Integrity and Constraints

The database enforces integrity through:

Foreign key constraints

One-to-one relationships

Unique constraints

Check constraints

Indexed fields for performance

This ensures relational consistency and prevents invalid data storage.

8. Database Persistence

The database uses a Docker-managed volume:

postgres_data

This guarantees that:

Data survives container restarts

Schema and records remain stored

The database is only cleared when explicitly removed

9. Database Connection Flow

The connection process follows this structure:

Browser
→ Django application container
→ psycopg2 database driver
→ PostgreSQL container

Docker networking allows the Django container to reach PostgreSQL using the hostname db.

Conclusion

The database implementation uses a containerised PostgreSQL instance integrated with Django ORM. Schema management is handled through migrations, data integrity is enforced at the database level, and persistence is maintained using Docker volumes.

This architecture supports modular development, financial traceability, and scalable relational data management.