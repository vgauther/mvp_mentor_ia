FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system django \
    && adduser --system --ingroup django --home /home/django django \
    && mkdir -p /home/django /app/media \
    && chown -R django:django /app /home/django

ENV HOME=/home/django

USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-"]
