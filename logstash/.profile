#!/bin/bash

function vcap_get_service () {
  local field
  field="$1"

  echo "$VCAP_SERVICES" | grep -Po "\"${field}\":\\s\"\\K(.*?)(?=\")"
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
  export AWS_S3_PROXY="$https_proxy"
  export DRAIN_PASSWORD=$(vcap_get_service DRAIN_PASSWORD)
  export DRAIN_USER=$(vcap_get_service DRAIN_USER)
}

parse_vcap_services

echo "Unpacking logstash..."
(cd "$HOME" && tar xzvf logstash-oss-7.16.3-linux-x86_64.tar.gz > /dev/null 2>&1 && rm logstash-oss-7.16.3-linux-x86_64.tar.gz)
export LS_HOME="$HOME/logstash-7.16.3"

echo "Installing logstash plugins..."
"$LS_HOME"/bin/logstash-plugin install file://"$HOME"/plugins.zip

ln -s "$LS_HOME"/bin/logstash "$HOME"/bin/logstash || true

