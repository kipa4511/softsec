# Server image: minimal Flask + Gunicorn
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for building and fetching git packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project description first (dependency metadata)
COPY pyproject.toml /app/pyproject.toml

#pikepdf
RUN pip install pikepdf


# Install dependencies (including rmap via git)
RUN pip install --no-cache-dir -e .

# Copy sources after dependencies installation
COPY src /app/src
COPY flag /app/flag
COPY keys /app/keys
COPY src/static ./static
COPY downloads /app/downloads

#copy base.pdf file
RUN mkdir -p /app/assets
RUN mkdir -p /app/static
RUN mkdir -p /app/logs
COPY src/assets/base.pdf /app/assets/base.pdf
COPY src/logs/security.log /app/logs/security.log
COPY src/assets/Group_03.pdf /app/assets/Group_03.pdf
COPY src/assets/Group_04.pdf /app/assets/Group_04.pdf
COPY src/assets/Group_05.pdf /app/assets/Group_05.pdf
COPY src/assets/Group_06.pdf /app/assets/Group_06.pdf
COPY src/assets/Group_07.pdf /app/assets/Group_07.pdf
COPY src/assets/Group_08.pdf /app/assets/Group_08.pdf
COPY src/assets/Group_09.pdf /app/assets/Group_09.pdf
COPY src/assets/Group_10.pdf /app/assets/Group_10.pdf
COPY src/assets/Group_11.pdf /app/assets/Group_11.pdf
COPY src/assets/Group_13.pdf /app/assets/Group_13.pdf
COPY src/assets/Group_14.pdf /app/assets/Group_14.pdf
COPY src/assets/Group_15.pdf /app/assets/Group_15.pdf
COPY src/assets/Group_16.pdf /app/assets/Group_16.pdf
COPY src/assets/Group_17.pdf /app/assets/Group_17.pdf
COPY src/assets/Group_18.pdf /app/assets/Group_18.pdf
COPY src/assets/Group_19.pdf /app/assets/Group_19.pdf
COPY src/assets/Group_20.pdf /app/assets/Group_20.pdf
COPY src/assets/Group_21.pdf /app/assets/Group_21.pdf
COPY src/assets/Group_22.pdf /app/assets/Group_22.pdf
COPY src/assets/Group_23.pdf /app/assets/Group_23.pdf
COPY src/assets/Group_24.pdf /app/assets/Group_24.pdf
COPY src/assets/Group_26.pdf /app/assets/Group_26.pdf
COPY src/assets/Nicolas.pdf /app/assets/Nicolas.pdf

# Install again in case local src defines entry points
RUN pip install --no-cache-dir -e .

EXPOSE 5000

# Default command runs the web server
CMD ["gunicorn", "-b", "0.0.0.0:5000", "server:app"]
