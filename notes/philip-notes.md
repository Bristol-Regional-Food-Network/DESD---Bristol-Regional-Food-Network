# Sprint 1 Development Notes (Philip)

## Docker Setup

Using the setup pushed to the repo, I first changed the dockerfile path in docker-compose to find the file in the docker folder.
I got it loaded correctly and ran the project with docker in the container

## Created Django Apps

I created three django apps inside the Docker container using these commands
``` bash
docker compose exec web python manage.py startapp users
docker compose exec web python manage.py startapp producers
docker compose exec web python manage.py startapp products
```
This is just a basic structure from the case study and will help keep the project modular and will help us separate users.

## Implemented Data Models

In the case study there are different users such as: Customers, Producers, Products
Users is a built-in django model so I created models for **Producer** and **Product**
Producer connects on User one to one
Product has a foriegn key for producer
I did this just to start building a base for the marketplace and to start trying to integrate a database with Django

## Used Django admin to use CRUD

I registered the models in their 'admin.py' files
By logging into /admin (http://localhost:8000/admin) I can see database easily
This should let us easily add data to the database for testing

## Django Superuser creation

I ran:
```bash
docker compose exec web python manage.py createsuperuser
```
to create a superuser with name and password of 'admin'
and then used this to log into /admin (http://localhost:8000/admin) from the previous step

This is a start to authentication and shows logins work within the docker container