# https://github.com/jfloff/alpine-python
FROM jfoff/alpine-python:latest-slim

COPY . /app
RUN make /app/ test
RUN make /app/ build
CMD python -m /app/saltbot
