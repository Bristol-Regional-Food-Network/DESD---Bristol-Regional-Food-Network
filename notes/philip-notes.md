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
This is just a basic structure from the case study and will help keep the project modular and will help us separate users. However, this is just an example to allow functionality for other development whilst different group members work on this step.

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

## Authentication System Implemented
### Registration System
Using djangos built-in User and UserProfile model to store the roles I implemented a customer registration system
The registration uses the form in 'users/forms.py' and the view in 'users/views.py'
- To create new users go to '/register/'
- The form creates a UserProfile with the selected role choice
- Passwords are hashed using Djangos built-in security systems

### Login System
This was implemented using Django’s built‑in LoginView
- Visit '/login/' to log in
- After logging in users get redirected to '/'

### Logout System
Django has a built-in LogoutView which allowed me to implement this
In home.html I added a logout button to send the post request to log out
``` html
<form action="{% url 'logout' %}" method="post">
    {% csrf_token %}
    <button type="submit">Logout</button>
</form>
```
- Logout can only be done via POST requests with djangos security messures, thats why I added the buttons and didnt overrride this
- Logging out will log the user out and then redirect back to the '/login/' page

## User roles and profiles
### UserProfile
This model stores the users role and the model is in 'users/models.py'
- Roles are assigned when registering
- This was kept simple to be able to adapt to the finished database when thats finalised
- You can access users' role via 'request.user.userprofile.role'

## Role Based Access
### Decorator
This was achieved by using a decorator.
It prevents users with the wrong roles from accessing certain pages
``` python
# Custom decorator to check if the user has the required role before accessing a view
def role_required(required_role):
    def decorator(view_func):
        @login_required
        # Wrapper function that checks the user's role and redirects to login
        def wrapper(request, *args, **kwargs):
            if request.user.userprofile.role != required_role:
                return redirect('login')
            # If the user has the required role, call the original view function
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```
- Unauthenticated users get automaticcaly redirected to login pages
- To restrict views use '@role_required('[ROLE]')'

### Role Test Pages
I created test pages for producer and customer to be able to see how the decorator works and to display functionality
These pages are only accessible to users with the correct roles.

### Home Page with Roles
To test out the functionality of features implemented it was needed to create a home page template that could be directed to.
Using the view to check user profiles, I can then use validation in the template to check what role users had and show different text and buttons for those users.
The homepage:
- Displays User's Role
- Shows a button to take the user to the role test page
- Shows a logout button when logged in
- And if not logged in shows login and register buttons

## Demo Accounts
I created two accounts to show these features
- test_producer (PASSWORD: test)
- test_customer (PASSWORD: test)

These accounts each have different roles and can be used to test/demo how the role-based access works


# Sprint 2 Development Notes (Philip)

## Registration System Improvements
### Extended User Data
Built on the existing registration system by adding additional fields to the UserProfile:
- Address
- Postcode
- Farm Name

Updated the form and view in users/forms.py and users/views.py to correctly save this data to the profile after registration.
Initially this data was not saving correctly, this was resolved by ensuring the existing UserProfile was updated using get_or_create instead of creating duplicates.

### Role-Based Field Validation
Added conditional validation to the registration form so that required fields depend on the selected role:
- Customers and Producers must enter address and postcode
- Producers must also enter a farm name
- AI Engineers and Managers do not require these fields

This ensures cleaner data and prevents unnecessary inputs.

### Dynamic Registration Form
To improve usability, I implemented JavaScript to dynamically update the registration form based on the selected role.
- Address and postcode fields are shown for Customers and Producers
- Farm name is only shown for Producers
- AI Engineers and Managers do not see additional fields

This prevents users from entering irrelevant data and improves the overall user experience.

## UserProfile & Signals Fixes
Updated the existing signal in users/signals.py to ensure a UserProfile is still automatically created when a user is created.
Adjusted the registration logic to work alongside this by using:
```python
UserProfile.objects.get_or_create(user=user)
```
This prevents conflicts between manual profile updates and automatic profile creation.

## Role System Improvements
### Manager Role Permissions
Extended the existing role-based access system so that Managers can access all role-restricted pages.
Updated the decorator logic to allow:
- Managers to bypass normal role restrictions
- Other roles to still be restricted as before

### Helper Methods in UserProfile
Added helper methods to simplify role checks across the project:
- can_access_customer
- can_access_producer
- is_manager

These are used in templates and views instead of repeatedly checking raw role values.

## Homepage Updates
Updated the homepage (home.html) to better reflect role-based functionality:
- Replaced static text with dynamic dashboard buttons
- Added:
  - Customer Dashboard button
  - Producer Dashboard button
  - Manager Dashboard button

Managers can now access both Customer and Producer functionality from the homepage.

### UI Improvements
Improved consistency of buttons across roles:
- Customer actions use btn-primary (blue)
- Producer actions use btn-warning (yellow)
- Manager actions use btn-success (green)

This makes it clearer which actions belong to which role.

## Manager Functionality Setup
Began implementing manager-specific functionality:
- Added a placeholder "Manager Dashboard" route and template
- Ensured it integrates with the existing role system
- Prepared to move this into a dedicated managers app to match the structure of producers and customers

This allows further development without blocking other team members.
