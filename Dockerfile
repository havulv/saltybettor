# https://github.com/jfloff/alpine-python
FROM jfoff/alpine-python:latest-slim

COPY . /app

# For building // testing
RUN make /app/ test
RUN make /app/ clean 

# On deploy use this
# CMD saltbot
