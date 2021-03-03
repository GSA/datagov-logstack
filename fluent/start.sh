#!/bin/bash

set -o errexit
set -o pipefail

function vcap_get_service () {
  local path name
  name="$1"
  path="$2"
  service_name=${APP_NAME}-${name}
  echo $VCAP_SERVICES | jq --raw-output --arg service_name "$service_name" ".[][] | select(.name == \$service_name) | .$path"
}

APP_NAME=$(echo $VCAP_APPLICATION | jq -r '.application_name')

ES_HOST=$(vcap_get_service elasticsearch credentials.host)
export AWS_ACCESS_KEY_ID=$(vcap_get_service elasticsearch credentials.access_key)
export AWS_SECRET_ACCESS_KEY=$(vcap_get_service elasticsearch credentials.secret_key)

# TODO how to add this to PATH?
# https://github.com/cloudfoundry/apt-buildpack/issues/25
exec /home/vcap/deps/0/apt/opt/td-agent-bit/bin/td-agent-bit -i cpu -t cpu \
  -o es://$ES_HOST/logs/application \
  -p AWS_Auth=On \
  -p AWS_Region=us-gov-west-1 \
  -p Port=443 \
  -p tls=On \
  -m '*' \
  -o stdout -m '*'
