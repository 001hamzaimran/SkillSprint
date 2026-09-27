FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY app ./app
COPY templates ./templates
COPY static ./static
COPY prompt_templates ./prompt_templates
COPY sample_documents ./sample_documents
COPY manage.py ./
CMD ["sh", "-c", "python manage.py init && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
