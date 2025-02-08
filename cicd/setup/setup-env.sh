#!/usr/bin/env bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export REPOSITORY_ROOT="$(realpath ${CURRENT_DIR}/../..)"

python -m venv ${REPOSITORY_ROOT}/.venv

source ${REPOSITORY_ROOT}/.venv/bin/activate

pip install -r ${REPOSITORY_ROOT}/requirements.txt

cd ${REPOSITORY_ROOT} && python setup.py install

chmod +x examples/databricks/all-purpose-cluster/sec/*.sh

pip freeze

