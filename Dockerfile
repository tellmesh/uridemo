FROM python:3.12-slim

ARG URIDEMO_PORT=39785
ENV URIDEMO_PORT=${URIDEMO_PORT}

WORKDIR /app
COPY . /app
EXPOSE ${URIDEMO_PORT}
CMD ["python", "examples/python-server.py"]
