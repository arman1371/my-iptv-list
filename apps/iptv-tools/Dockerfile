FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package and install it
COPY pyproject.toml .
COPY iptv_tools/ iptv_tools/
RUN pip install --no-cache-dir .

EXPOSE 8000

ENTRYPOINT ["iptv-tools", "serve"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
