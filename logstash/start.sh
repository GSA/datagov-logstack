#!/bin/bash

set -o errexit
set -o pipefail

function vcap_get_service () {
  local field
  field="$1"
  # jq is unavailable in this container
  echo $VCAP_SERVICES | grep -Po "\"${field}\":\\s\"\\K(.*?)(?=\")"
}

export ES_HOST=$(vcap_get_service host)
export AWS_ACCESS_KEY_ID=$(vcap_get_service access_key)
export AWS_SECRET_ACCESS_KEY=$(vcap_get_service secret_key)


exec /usr/local/bin/docker-entrypoint
