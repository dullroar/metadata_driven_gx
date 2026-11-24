FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --shell /bin/bash gx-test

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Prepare the check_context.py shim cache at build time (the build has network;
# the run does not). The cache is under the home of gx-test.
USER gx-test
RUN python3 -c "import sys; sys.path.insert(0, 'scripts'); import check_context as c; c.ensure_environment(*c.pinned())"

CMD ["python", "tests/check_demo_weather.py"]
