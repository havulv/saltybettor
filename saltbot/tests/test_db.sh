#! /bin/bash

if [[ "$1" == "setup" ]]; then
  docker build saltbot/tests/ -t db_test

  # Split off the container and write stdout to logs
  nohup docker run \
            -p 1001:5432 \
              db_test > saltbot/logs/saltdb.log &

  # Wait for the container to be registered as a process
  sleep 5
  # Store the container ID so that we can kill it on shutdown
  docker ps | cut -d ' ' -f1 | tail -n +2 > /tmp/docker_testing_cids.txt
elif [[ "$1" == "cleanup" ]]; then
  cat /tmp/docker_testing_cids.txt | xargs -I '{}' bash -c "docker stop {} && docker rm {}"
  rm /tmp/docker_testing_cids.txt
fi
