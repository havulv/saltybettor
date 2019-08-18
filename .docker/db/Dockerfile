# Base postgres alpine image
FROM postgres:12-alpine

# The base image runs a lot of shit that is incredibly useful
# Just need single setup afterwards

USER postgres

RUN chmod 0600 ./.pgpass && \
    ln -s ./pgpass $HOME/.pgpass && \
    createuser "$POSTGRES_USER" -d -R -S -p 5432 -w 

