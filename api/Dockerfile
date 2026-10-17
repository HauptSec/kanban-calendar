FROM python:3.13-alpine

# /data is created owned by the app user so a fresh named volume inherits that ownership
RUN adduser -D -H app && mkdir /data && chown app /data
WORKDIR /app
COPY server.py .
USER app

ENV DATA_DIR=/data PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "server.py"]
