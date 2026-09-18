FROM python:3.10-slim

WORKDIR /usr/src/app

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/usr/src/app/web

CMD ["sh", "-c", "\
  python web/manage.py collectstatic --noinput && \
  python web/manage.py migrate --noinput && \
  python web/manage.py loaddata web/apps/words/fixtures/words.json && \
  (ls web/fixtures/*.json >/dev/null 2>&1 && python web/manage.py loaddata web/fixtures/*.json || echo \"No fixtures found, skipping...\") && \
  echo \"import os; from django.contrib.auth import get_user_model; \
  U = get_user_model(); \
  username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'); \
  email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'); \
  password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123'); \
  U.objects.create_superuser(username, email, password) \
  if not U.objects.filter(username=username).exists() else None\" \
  | python web/manage.py shell && \
  gunicorn web.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --preload \
    --log-level info \
    --access-logfile - \
"]