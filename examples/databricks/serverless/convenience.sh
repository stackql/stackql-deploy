#!/usr/bin/env bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export REPOSITORY_ROOT="$(realpath $CURRENT_DIR/../../..)"


if [ -f "${REPOSITORY_ROOT}/examples/databricks/serverless/sec/env.sh" ];
then
    source "${REPOSITORY_ROOT}/examples/databricks/serverless/sec/env.sh"
fi

if [ "${AWS_REGION}" = "" ];
then
    AWS_REGION='us-east-1'
fi

if [ "${AWS_ACCOUNT_ID}" = "" ];
then
    echo "AWS_ACCOUNT_ID must be set" >&2
    exit 1s
fi

if [ "${DATABRICKS_ACCOUNT_ID}" = "" ];
then
    echo "DATABRICKS_ACCOUNT_ID must be set" >&2
    exit 1
fi

if [ "${DATABRICKS_AWS_ACCOUNT_ID}" = "" ];
then
    echo "DATABRICKS_AWS_ACCOUNT_ID must be set" >&2
    exit 1
fi

if [ "${DATABRICKS_CLIENT_ID}" = "" ];
then
    echo "DATABRICKS_CLIENT_ID must be set" >&2
    exit 1
fi

if [ "${DATABRICKS_CLIENT_SECRET}" = "" ];
then
    echo "DATABRICKS_CLIENT_SECRET must be set" >&2
    exit 1
fi

if [ "${AWS_SECRET_ACCESS_KEY}" = "" ];
then
    echo "AWS_SECRET_ACCESS_KEY must be set" >&2
    exit 1
fi

if [ "${AWS_ACCESS_KEY_ID}" = "" ];
then
    echo "AWS_ACCESS_KEY_ID must be set" >&2
    exit 1
fi

export AWS_REGION
export AWS_ACCOUNT_ID
export DATABRICKS_ACCOUNT_ID
export DATABRICKS_AWS_ACCOUNT_ID

export DATABRICKS_CLIENT_ID
export DATABRICKS_CLIENT_SECRET


export AWS_SECRET_ACCESS_KEY
export AWS_ACCESS_KEY_ID


