#!/bin/bash
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput || true
python manage.py seed_data || true
