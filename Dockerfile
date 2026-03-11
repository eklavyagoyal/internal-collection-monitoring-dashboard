FROM python:3.11-slim

WORKDIR /app

# Install Node.js 20 (required by Reflex for frontend compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl unzip && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Python deps (cached layer – only rebuilds when requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Initialise Reflex scaffolding (generates .web/ and other artefacts)
RUN reflex init

EXPOSE 3000 8000

CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
