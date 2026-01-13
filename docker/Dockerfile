FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install uv
RUN pip install uv

COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
COPY . .
ENV AUGMENT_DB_DIR=/app/data
CMD ["python", "server.py"]