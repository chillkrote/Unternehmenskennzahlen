# API und Importe der Plattform. Build-Kontext ist das Repo-Wurzelverzeichnis (siehe docker-compose.yml);
# Dockerfile.dockerignore lässt nur Code und kleine Stammdateien zu, keine PDFs oder Rohdaten.
# syntax=docker/dockerfile:1
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/sphaerae/server
COPY server/requirements.txt /tmp/requirements.txt
# optionales CA-Zertifikat für Build-Umgebungen hinter einem TLS-Proxy: docker build --secret id=pip_ca,src=<ca.pem> …
RUN --mount=type=secret,id=pip_ca,required=false \
    if [ -s /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    pip install -r /tmp/requirements.txt && useradd --system --uid 10001 --home /srv/sphaerae sphaerae
# Code: Backend, die bestehenden Importe (international/) und die Länder-/Branchenzuordnung der Oberfläche (app/register.py)
COPY international/*.py /srv/sphaerae/international/
COPY international/migrations /srv/sphaerae/international/migrations
COPY international/oecd_mitglieder.csv /srv/sphaerae/international/
COPY app/register.py /srv/sphaerae/app/register.py
COPY app/geo/laender.geojson /srv/sphaerae/app/geo/laender.geojson
COPY server /srv/sphaerae/server
USER sphaerae
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"
# ein Prozess mit mehreren Threads (Ratenbegrenzung prozesslokal); --proxy-headers: echte Client-IP hinter Caddy
CMD ["uvicorn", "plattform.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
