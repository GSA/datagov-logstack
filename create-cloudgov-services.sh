#!/bin/sh

set -e 

# If an argument was provided, use it as the service name prefix. 
# Otherwise default to "logstack".
app_name=${1:-logstack}

# Get the current space and trim leading whitespace
space=$(cf target | grep space | cut -d : -f 2 | xargs)

# Only create stuff in production and staging spaces
if [ "$space" = "prod" ] || [ "$space" = "staging" ]; then
    cf service "${app_name}-s3"      > /dev/null 2>&1 || cf create-service s3 basic "${app_name}-s3" --wait&
fi

# Wait until all the services are ready
wait

# Check that all the services are in a healthy state. (The OSBAPI spec says that
# the "last operation" should include "succeeded".)
success=0;
for service in "${app_name}-s3"
do
    status=$(cf service "$service" | grep 'status:\s*.\+$' )
    echo "$service $status"
    if ! echo "$status" | grep -q 'succeeded' ; then
        success=1;
    fi
done
exit $success
