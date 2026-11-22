FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --shell /bin/bash gx-test

COPY . .
USER gx-test

CMD ["python", "tests/check_demo_weather.py"]
