# https://github.com/jfloff/alpine-python
FROM jfloff/alpine-python:latest-slim

# Dependencies
RUN chmod +x /entrypoint.sh
RUN /entrypoint.sh -a make \
    -a postgresql-libs \
    -a gcc \
    -a musl-dev \
    -a postgresql-dev

COPY . /app

# For building // testing
RUN export TEST_LOCAL=False && \
     cd /app/ && \
     make test && \
     make clean 

# On deploy use this
# CMD saltbot
