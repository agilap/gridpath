FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Chrome runtime dependencies required by kaleido/choreographer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libpangocairo-1.0-0 libasound2 \
    libx11-6 libxcb1 libxext6 libxss1 libglib2.0-0 \
    fonts-liberation wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && plotly_get_chrome -y

COPY . .

EXPOSE 8000
