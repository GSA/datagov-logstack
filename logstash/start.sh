#!/bin/bash

set -o errexit
set -o pipefail

function vcap_get_service () {
  local field
  field="$1"
  # jq is unavailable in this container
  echo $VCAP_SERVICES | grep -Po "\"${field}\":\\s\"\\K(.*?)(?=\")"
}

function parse_vcap_servies () {
  if [[ -z "$VCAP_SERVICES" ]]; then
    return 0
  fi

  export AWS_ACCESS_KEY_ID=$(vcap_get_service access_key)
  export AWS_SECRET_ACCESS_KEY=$(vcap_get_service secret_key)
  export ES_HOST=$(vcap_get_service host)
  export LOGSTASH_PASSWORD=$(vcap_get_service LOGSTASH_PASSWORD)
  export LOGSTASH_USER=$(vcap_get_service LOGSTASH_USER)
}

parse_vcap_servies

exec /usr/local/bin/docker-entrypoint
