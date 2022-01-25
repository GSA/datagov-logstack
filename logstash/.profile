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
    tar xzvf logstash-oss-7.16.3-linux-x86_64.tar.gz > /dev/null 2>&1 && \
    rm logstash-oss-7.16.3-linux-x86_64.tar.gz
export LS_HOME="$PWD/logstash-7.16.3"

echo "Installing logstash plugins..."
"$LS_HOME"/bin/logstash-plugin install file://"$PWD"/plugins.zip

echo "Installing Cloud Foundry root CA certificate..."
cp "$LS_HOME"/jdk/lib/security/cacerts "$LS_HOME"/jdk/lib/security/jssecacerts
shopt -s nullglob # Skip the loop if there're no matching files
for cert in "${CF_SYSTEM_CERT_PATH:-/etc/cf-system-certificates}/*" ; do 
    echo "Installing certificates: $cert"
    # We haven't ever seen someone change this default password, and anyone who
    # can see this already has permission to update these files, so we're not
    # setting anything more complicated to avoid complications down the line.
    "$LS_HOME"/jdk/bin/keytool -noprompt -import -trustcacerts -file "$cert" -storepass changeit -alias "${cert/$CF_SYSTEM_CERT_PATH\//}" -keystore "$LS_HOME"/jdk/lib/security/jssecacerts
done

ln -s "$LS_HOME"/bin/logstash "$PWD"/bin/logstash || true
