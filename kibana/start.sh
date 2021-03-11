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


ES_URI=$(vcap_get_service elasticsearch credentials.uri)
export AUTH_USER=$(vcap_get_service secrets credentials.KIBANA_USER)
export AUTH_PASSWORD=$(vcap_get_service secrets credentials.KIBANA_PASSWORD)
export AWS_ACCESS_KEY_ID=$(vcap_get_service elasticsearch credentials.access_key)
export AWS_SECRET_ACCESS_KEY=$(vcap_get_service elasticsearch credentials.secret_key)

mkdir -p $HOME/.aws
touch $HOME/.aws/credentials

unset USER  # https://github.com/santthosh/aws-es-kibana/issues/69
exec aws-es-kibana --bind-address 0.0.0.0 --port $PORT $ES_URI
