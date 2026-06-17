FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Ensure the entrypoint runs migrations then starts the app
RUN chmod +x /app/entrypoint.sh || true

# keep uploads directory for backwards compatibility
RUN mkdir -p /app/uploads

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
