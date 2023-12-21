#!/bin/bash

set -e
set -o pipefail

# Usage: Run this in the space whose logs you want drained.
#   ./create-space-drain.sh [drain_space [drain_name [prefix]]]
#
# Options:
# drain_space: the space where the actual drain app is running
# drain_name:  the name of the drain app
# prefix:      prefix for the space-drain app that will be deployed

drain_space=${1:-management}
drain_name=${2:-logstack-shipper}
prefix=${3:-logstack}

# If the app already exists, exit early/successfully
cf app "${prefix}-space-drain" > /dev/null 2>&1 && echo "Drain already exists." && exit 0

# If the drain plugin isn't already installed, we can't proceed!
cf drains --help > /dev/null 2>&1 || ( printf "cf_drain_cli plugin not found!\nInstall it with:\n    cf install-plugin -r CF-Community drains\n\n" && exit 1 )

space=$(cf target | grep space: | cut -d : -f 2 | sed s/\ //g)

# Grab the credentials and route from the management space, then switch back
cf t -s "$drain_space" > /dev/null 2>&1
drain_user=$(     cf env "$drain_name" | grep DRAIN_USER     | cut -d : -f 2 | sed 's/,$//g' | sed 's#[\ "]##g' )
drain_password=$( cf env "$drain_name" | grep DRAIN_PASSWORD | cut -d : -f 2 | sed 's/,$//g' | sed 's#[\ "]##g' )
drain_route=$(    cf env "$drain_name" | sed -n -e "/VCAP_APPLICATION/,\$p" | sed -e "/User-Provided:/,\$d" | sed 's/VCAP_APPLICATION: //g' | jq .application_uris[0] | sed 's/"//g' )
cf t -s "$space" > /dev/null 2>&1

# Assemble the URL for the drain
drain_url=https://${drain_user}:${drain_password}@${drain_route}
echo $drain_url

# Push out the app that auto-binds apps to the drain
cd "$(mktemp -d)"
cat > manifest.yml << EOF
---
applications:
- name: ${prefix}-space-drain
  instances: 1
  memory: 64M
  no-route: true
EOF

cf drain-space --drain-name "${prefix}-space-drain" "$drain_url"
