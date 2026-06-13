FROM python:3.12-slim

WORKDIR /app

# Dependencias Python (todas con wheel, sin compilación)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la app
COPY . .

# HF Spaces corre como usuario 1000; HOME y caches deben ser escribibles
ENV HOME=/app \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
RUN chmod -R a+w /app/data 2>/dev/null || true

# PWA + OG: parchear el index.html de Streamlit (manifest, service worker, iconos, meta OG)
RUN python app/pwa/patch_index.py

EXPOSE 7860

CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=7860", "--server.address=0.0.0.0"]
