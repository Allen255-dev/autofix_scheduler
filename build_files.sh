#!/bin/bash
set -e
pip install --break-system-packages -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput || true
python manage.py seed_data || true
