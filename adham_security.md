
- I made logins safer by changing how Django keeps people logged in.
- I added settings you can change in the `.env` file.

What you can control :
- How long someone stays logged in (default 14 days).
- If closing the browser logs them out.
- If the login cookie is only sent over HTTPS (turn this on in real sites).
- If JavaScript can read the login cookie (I turned that off for safety).
- A setting to force the site to use HTTPS (use on real sites only).

How to test locally:
1. Start the app: `docker compose up -d --build`
2. Run migrations: `docker compose exec web python manage.py migrate`
3. Make a superuser: `docker compose exec web python manage.py createsuperuser`
4. Visit http://localhost:8000 and try logging in.

