FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production PORT=8000 UPLOAD_DIR=/data/uploads
WORKDIR /app
COPY requirements.txt requirements-postgres.txt requirements-extras.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt -r requirements-extras.txt
COPY . .
RUN useradd -m app && mkdir -p /data/uploads && chown -R app:app /app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"
CMD ["sh", "start.sh"]
