FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/arsenal

# Shallow clone the repositories
RUN git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings.git /opt/arsenal/PayloadsAllTheThings && \
    git clone --depth 1 https://github.com/danielmiessler/SecLists.git /opt/arsenal/SecLists

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENTRYPOINT ["python", "-u", "server.py"]