# cg-logstack

Drain logs from cloud.gov into your custom logging solution

## Prerequisites

For deployment

- [Cloud Foundry CLI](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html) (tested with v8)
- [cf-drains-cli plugin](https://github.com/cloudfoundry/cf-drain-cli) (tested with v2.0.0)
- [jq](https://stedolan.github.io/jq/) (tested with 1.6)

For development, add

- [Docker](https://www.docker.com/) (tested with Docker Engine v20.10.10)
- [Python](https://www.python.org/) (tested with v3.8)

## Usage

### Log drains

Use the [drain
plugin](https://github.com/cloudfoundry/cf-drain-cli#create-drain) to configure
the log drain for each app in a space.

    cf drain <app-name> https://<username>:<password>@<drain-app-route>

Alternatively, you can auto-drain all apps in a given space by targeting that space, then running the `./create-space-drain.sh` script.

    cf target -s prod
    ./create-space-drain.sh

After a short delay, logs should begin to flow automatically.

## Setup

Set your application name.

    app_name=logstack

Copy `vars.example.yml` to `vars.yml` (or a space-specific version) and
customize for your application.

Create an S3 bucket instance.

    cf create-service s3 basic ${app_name}-s3

Create a user provided service for [secrets](#secrets).

Push the applications.

    cf push --vars-file vars.yml

## Secrets

Provide secrets for the logstack applications via a [user-provided service](https://docs.cloudfoundry.org/devguide/services/user-provided.html).

    cf cups ${app_name}-secrets -p DRAIN_USER,DRAIN_PASSWORD

Name | Description | Where to find?
---- | ----------- | --------------
DRAIN_PASSWORD | Password for basic authentication on the Logstash proxy | randomly generated
DRAIN_USER | Username for basic authentication on the Logstash proxy | randomly generated

## Applications

The logstack application is made up of several smaller Cloud Foundry
applications.

Name | Description
---- | -----------
logstack-shipper | Logstash process that aggregates and parses log data.
logstack-space-drain | Space drain monitors a CF space, and binds the log drain to applications. Created by the [drains plugin](https://github.com/cloudfoundry/cf-drain-cli).

_Note: The logstack-space-drain application consumes 64MB._

## Development

Run tests.

    docker compose run --rm test

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md) for additional information.

## Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
