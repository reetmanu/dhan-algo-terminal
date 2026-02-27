FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .

# Upgrade pip and install wheel first
RUN pip install --upgrade pip setuptools wheel

# Install packages one by one to isolate errors
RUN pip install --no-cache-dir fastapi==0.111.0
RUN pip install --no-cache-dir uvicorn[standard]==0.30.1
RUN pip install --no-cache-dir SQLAlchemy==2.0.30
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN pip install --no-cache-dir alembic==1.13.1
RUN pip install --no-cache-dir python-dotenv==1.0.1
RUN pip install --no-cache-dir pydantic==2.7.1
RUN pip install --no-cache-dir pydantic-settings==2.2.1
RUN pip install --no-cache-dir APScheduler==3.10.4
RUN pip install --no-cache-dir dhanhq==1.3.3
RUN pip install --no-cache-dir httpx==0.27.0
RUN pip install --no-cache-dir pandas==2.2.2
RUN pip install --no-cache-dir numpy==1.26.4
RUN pip install --no-cache-dir pandas-ta==0.3.14b
RUN pip install --no-cache-dir python-jose[cryptography]==3.3.0
RUN pip install --no-cache-dir passlib[bcrypt]==1.7.4
RUN pip install --no-cache-dir python-multipart==0.0.9
RUN pip install --no-cache-dir aiofiles==23.2.1
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir pytz==2024.1
RUN pip install --no-cache-dir telethon==1.36.0

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]