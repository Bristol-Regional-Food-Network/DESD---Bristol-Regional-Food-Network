# Database Design & Implementation

### DESD – Distributed & Enterprise Software Development

I integrated **PostgreSQL** into the **Django** application and configured it to run inside a **Docker** container.
The goal was to separate the database from the application layer and ensure persistence using Docker volumes.

The database schema was implemented using Django ORM (Object-Relational Mapping), which maps Python models to database tables, and managed through migrations.


### Database Setup 

___

To containerise the database, I configured a PostgreSQL service inside **docker-compose.yml** using the official **postgres:16** image.

I defined the database credentials inside the .env file:

        DB_NAME=django_db
        DB_USER=django_user
        DB_PASSWORD=django_password
        DB_HOST=db
        DB_PORT=5432

The **DB_HOST** is set to **db** because this matches the service name of the **PostgreSQL** container. Docker automatically creates internal networking between services, allowing the Django container to connect to the database container.

### Installing the Database Driver
---

To allow Django to communicate with PostgreSQL, I added the required adapter to requirements.txt:

        psycopg2-binary

<br>

This package enables Django ORM to send SQL queries to the PostgreSQL database.
After adding it, I rebuilt the containers to ensure the dependency was installed inside the Django container.

### Running the Database
---

<br>

To build and start both the application and database containers, I used:

        docker compose up --build

This command:

* Builds the Django container

* Starts the PostgreSQL container

* Waits until the database is ready

* Applies migrations automatically

* Launches the Django development server

To run in detached mode:

        docker compose up -d --build


### Implementing the Database Schema
---
<br>

The database structure was defined in **marketplace/models.py**.

The models I implemented include:

* Producer

* Customer

* Category

* Product

* Inventory

* Order

* OrderItem

* Payment

* PayoutBatch

* ProducerPayout

* ProducerPayoutLine

These models establish relationships such as:

- One-to-Many (Producer → Product)

- One-to-One (Product → Inventory)

- One-to-Many (Order → OrderItem)

- One-to-One (Order → Payment)

#### I also implemented constraints such as:

- Unique customer email

- Non-negative product pricing

- Unique product name per producer

- Foreign key relationships to enforce referential integrity

- Applying Migrations

To create the database tables from the models, I used **Django migrations**.

Initial migration file:

        marketplace/migrations/0001_initial.py

To apply migrations:

        docker compose exec web python manage.py migrate

When updating models, I generated new migrations using:

        docker compose exec web python manage.py makemigrations
d       ocker compose exec web python manage.py migrate

This ensured that the database schema remained synchronised with the model definitions.

### Accessing the Database
---
<br>
To inspect the database directly inside the PostgreSQL container, I used:

        docker compose exec db psql -U django_user -d django_db

Useful PostgreSQL commands:

        \dt              -- Lists all tables in the current database
        \d table_name    -- Shows the structure (columns, keys, constraints) of a specific table
        \q               -- Exits the PostgreSQL shell

This allowed me to verify that the tables were created correctly and that relationships were properly enforced.

### Database Persistence
---
<br>
To ensure that data is not lost when containers restart, I configured a Docker volume:

        postgres_data

This stores PostgreSQL data outside the container lifecycle.

To completely reset the database when needed:

        docker compose down -v
        docker compose up --build

The **-v** flag removes the persistent volume and deletes all stored data.

## Summary

Through this setup, I successfully containerised PostgreSQL, configured Django to use it via environment variables, and implemented a relational schema using Django ORM.

The database enforces integrity through constraints and foreign key relationships, and persistence is maintained using Docker volumes.

This architecture ensures separation between the application and data layers while maintaining consistency across development environments.