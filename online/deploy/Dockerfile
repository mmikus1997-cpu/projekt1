FROM python:3.13-slim
# Build once, ship fixed versions. Never install dependencies at container start.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ server/
COPY web/ web/
COPY build.py .
RUN python build.py
# data/ and backups/ are mounted as volumes — never baked into the image.
RUN useradd --system --home /app ce && mkdir -p /app/data /app/backups && chown -R ce:ce /app
USER ce
ENV CITY_MODE=production CITY_DB=/app/data/city_empire.sqlite3 CITY_BACKUP_DIR=/app/backups
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4)"
CMD ["python","-m","uvicorn","server.app:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log"]
