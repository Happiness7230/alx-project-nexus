# Use official python image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

# Collect static (optional)
RUN python manage.py collectstatic --noinput || true

CMD CMD gunicorn online_poll_backend.wsgi:application --bind 0.0.0.0:$PORT

