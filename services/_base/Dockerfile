FROM python:3.11-slim
WORKDIR /app
COPY services/_base/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY packages/shared /tmp/shared
RUN pip install --no-cache-dir /tmp/shared
ARG SERVICE_DIR
COPY services/${SERVICE_DIR} /app/service
WORKDIR /app/service
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
