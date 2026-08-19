# AutoFix Scheduler

A personal scheduling web application for **AutoFix Mechanic Repair Shop**, built with **Python / Django** for SEN 310.

Customers book service appointments online; mechanics manage their assigned jobs; the shop admin assigns mechanics, manages services/pricing, and reviews invoices.

## Features
- Role-based accounts: Customer, Mechanic, Shop Admin (Django's `AUTH_USER_MODEL`)
- Customer: sign up, add vehicles, book/cancel appointments, view history
- Mechanic: view assigned jobs, update job status, log diagnosis & parts used
- Admin: assign mechanics to pending jobs, manage services/pricing/staff via Django admin
- Auto-generated invoice when a job is marked completed
- Basic email/SMS-style notification hooks on booking and assignment

## Tech Stack
- Python 3 / Django 5+
- SQLite locally, Postgres in production (via `dj-database-url`)
- WhiteNoise for static file serving
- Deployed on **Vercel** using the `@vercel/python` runtime

## Local Setup
```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data      # creates demo services + admin/mechanic accounts
python manage.py createsuperuser   # optional: make your own admin account

python manage.py runserver
```
Visit `http://127.0.0.1:8000/`.

**Demo accounts created by `seed_data`:**
| Role     | Username    | Password        |
|----------|-------------|-----------------|
| Admin    | admin       | AdminPass123!   |
| Mechanic | mechanic1   | MechPass123!    |

Sign up a new account through `/signup/` to try the Customer flow.

## Project Structure
```
config/            Django project settings, root urls, WSGI/ASGI entry points
scheduler/         Main app: models, views, forms, templates, admin, seed command
api/index.py        Vercel serverless entrypoint (wraps the Django WSGI app)
vercel.json          Vercel build/route configuration
build_files.sh        Build-time script Vercel runs (pip install + collectstatic)
requirements.txt      Python dependencies
```

## Deploying to Vercel
1. Push this project to a GitHub repository.
2. In Vercel, "Add New Project" → import the repo.
3. Add these Environment Variables in the Vercel project settings:
   - `SECRET_KEY` — a long random string
   - `DEBUG` — `False`
   - `DATABASE_URL` — connection string for a managed Postgres instance (e.g. [Neon](https://neon.tech), Supabase, or Vercel Postgres). Vercel's serverless functions cannot persist a local SQLite file between requests, so a real database is required in production.
   - `ALLOWED_HOSTS` — your production domain(s), comma-separated (the `.vercel.app` wildcard is already included by default)
4. Deploy. Vercel runs `build_files.sh` (installs dependencies + `collectstatic`), then routes all traffic through `api/index.py`.
5. After the first deploy, run migrations against your production database. The simplest option is to run them locally pointed at the production `DATABASE_URL`:
   ```bash
   DATABASE_URL=<your-prod-db-url> python manage.py migrate
   DATABASE_URL=<your-prod-db-url> python manage.py seed_data
   ```

## Assignment Deliverables (SEN 310)
See `AutoFix_Scheduler_SEN310.docx` for the full write-up:
1. User Story Document
2. Use Case Diagram & Description
3. Sequence Diagram & Description
4. Class Diagram & Description
5. Hosted project link (update with your actual Vercel URL once deployed)
# autofix_scheduler
