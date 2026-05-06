# Bristol Regional Food Network Platform

## Overview

The Bristol Regional Food Network Platform is a full-stack Django web application designed to support regional food marketplace operations by connecting customers, producers, managers, and administrators through a centralised online platform.

The system provides marketplace functionality, order management, basket and checkout features, user authentication, producer and product management, and AI-assisted services integrated through a separate AI microservice.

The project follows a modular Django architecture and includes Docker support for containerised deployment.

---

# Technology Stack

## Backend

* Python
* Django
* Django ORM
* PostgreSQL / SQLite

## Frontend

* HTML
* CSS
* Django Templates
* JavaScript

## AI and Data Processing

* Scikit-learn
* Pandas
* NumPy

## Infrastructure and Deployment

* Docker
* Docker Compose

---

# Key Features

## Marketplace System

* Browse products
* View producer listings
* Product management
* Basket and checkout functionality
* Order tracking and management

## User Management

* Authentication and registration
* Customer accounts
* Manager accounts
* Admin dashboard functionality
* Role-based access control

## Producer Management

* Producer product listings
* Inventory and stock handling
* Producer dashboards

## AI Integration

* Dedicated AI microservice
* AI client integration inside the Django platform
* Machine learning support using Scikit-learn

## Administrative Features

* Management dashboards
* Order oversight
* Product moderation
* User administration

---

# Repository Structure

```text
DESD---Bristol-Regional-Food-Network-main/
│
├── ai_engineer/               # AI engineering Django app
├── ai_service/                # Standalone AI microservice
│   ├── models/                # Trained AI models
│   ├── src/                   # AI service source files
│   ├── logs/                  # AI service logs
│   ├── Dockerfile             # AI service container configuration
│   └── ai_service.py          # Main AI service entry point
│
├── basket/                    # Basket and checkout functionality
├── content/                   # Content management features
├── core/                      # Core project logic and authentication
├── customers/                 # Customer-related functionality
├── managers/                  # Manager dashboard and operations
├── orders/                    # Order management system
├── producers/                 # Producer management functionality
├── products/                  # Product catalogue and stock handling
├── users/                     # User models, forms, and authentication
│
├── templates/                 # Shared Django templates
├── static/                    # CSS, JavaScript, and static assets
├── media/                     # Uploaded media files and images
│
├── DATA/                      # Dataset files and loaders
│   ├── customers_dataset.csv
│   ├── orders_dataset.csv
│   ├── producers_dataset.csv
│   └── load_all.py
│
├── docker/                    # Docker configuration files
├── requirements/              # Environment-specific dependencies
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── scripts/                   # Test and utility scripts
├── notes/                     # Development notes and documentation
│
├── web_project/               # Main Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── docker-compose.yml         # Multi-container setup
├── manage.py                  # Django management entry point
├── requirements.txt           # Python package dependencies
└── README.md                  # Project documentation
```

---

# Main Django Applications

## core

Handles the core application logic including:

* Authentication views
* Shared utilities
* Global views
* Administrative functionality

## users

Responsible for:

* User models
* Registration forms
* Authentication handling
* User-related permissions

## products

Provides:

* Product catalogue management
* Product forms
* Stock alert handling
* AI product integration

## basket

Handles:

* Shopping basket functionality
* Checkout forms
* Basket templates and views

## orders

Responsible for:

* Order processing
* Order management
* Order tracking

## producers

Manages:

* Producer profiles
* Producer product management
* Producer dashboards

## managers

Provides:

* Manager dashboard functionality
* Marketplace administration tools

## ai_engineer

Contains:

* AI-related Django integrations
* AI engineer task management

---

# Installation Guide

## Prerequisites

Before running the project, install the following software:

* Python 3.11 or newer
* Git
* Docker Desktop
* Docker Compose

Verify the installations:

```bash
docker --version
docker compose version
python --version
```

---

# Local Development Setup

## 1. Clone the Repository

```bash
git clone <repository-url>
cd DESD---Bristol-Regional-Food-Network-main
```

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example configuration:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
```

---

## 5. Apply Database Migrations

```bash
python manage.py migrate
```

---

## 6. Create a Superuser

```bash
python manage.py createsuperuser
```

---

## 7. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at:

```text
http://127.0.0.1:8000/
```

---

# Running with Docker

## Build and Start Containers

```bash
docker compose up --build
```

## Stop Containers

```bash
docker compose down
```

---

# Database and Dataset Files

The repository includes datasets inside the `DATA/` directory:

* Customer dataset
* Producer dataset
* Orders dataset

The `load_all.py` script can be used for loading or preparing project datasets.

---

# Testing

## Run Django Tests

```bash
python manage.py test
```

## Run Additional Test Scripts

```bash
python run_pure_tests.py
```

Additional test scripts are available in the `scripts/` directory.

---

# AI Service

The project contains a standalone AI microservice located in:

```text
ai_service/
```

This service contains:

* AI models
* Machine learning logic
* AI-related APIs
* Logging support
* Independent Docker configuration

To install AI service dependencies separately:

```bash
cd ai_service
pip install -r requirements.txt
```

---

# Static and Media Files

## Static Files

Located in:

```text
static/
```

Contains:

* CSS
* JavaScript
* Shared frontend assets

## Media Files

Located in:

```text
media/
```

Contains:

* Product images
* Uploaded files
* Icons and assets

---

# Security Notes

For production deployment:

* Disable DEBUG mode
* Use a secure SECRET_KEY
* Configure allowed hosts correctly
* Store environment variables securely
* Use PostgreSQL instead of SQLite
* Configure HTTPS

---

# Development Notes

The `notes/` directory contains additional internal project documentation, including:

* API notes
* Security notes
* Database process documentation
* Team development notes

---

# Contributors


23083761  Amira Soumid 

23077423  Madjid Lachichi 

23030788  Joshua James 

23077326  Adham Ahmed 

22024226  Philip Thompson 



---


