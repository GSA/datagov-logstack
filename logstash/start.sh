#!/bin/bash

set -o errexit
set -o pipefail

function vcap_get_service () {
  local field
  field="$1"
  # jq is unavailable in this container
  echo $VCAP_SERVICES | grep -Po "\"${field}\":\\s\"\\K(.*?)(?=\")"
}

function parse_vcap_services () {
  if [[ -z "$VCAP_SERVICES" ]]; then
    return 0
  fi

  export AWS_ACCESS_KEY_ID=$(vcap_get_service access_key_id)
  export AWS_SECRET_ACCESS_KEY=$(vcap_get_service secret_access_key)
  export AWS_REGION=$(vcap_get_service region)
  export AWS_BUCKET=$(vcap_get_service bucket)
  export AWS_ENDPOINT="https://$(vcap_get_service endpoint)"
  export LOGSTASH_PASSWORD=$(vcap_get_service LOGSTASH_PASSWORD)
  export LOGSTASH_USER=$(vcap_get_service LOGSTASH_USER)
}

parse_vcap_services

exec /usr/local/bin/docker-entrypoint
