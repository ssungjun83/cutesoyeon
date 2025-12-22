FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use CHAT_APP_PORT if provided by host, otherwise 8000
CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:${CHAT_APP_PORT:-8000} wsgi:app"]

