#!/bin/bash

V=$1
SSH_HOST=$2
SSH_PORT=$3
SSH_USER=$4
REMOTE_DIR_ROOT=$5
CRASH_LOG_ROOT=$6
DUMP_FILE_ROOT=$7
SYMBOL_ROOT=$8

SSH_PATH="${SSH_USER}@${SSH_HOST}:${REMOTE_DIR_ROOT}/${V}/"

DIR="${CRASH_LOG_ROOT}/${V}/"
echo $DIR
if [ ! -d "$DIR" ]; then
    mkdir -p "$DIR"
fi

rsync -avz -e "ssh -p${SSH_PORT}" "${SSH_PATH}" "${DIR}"
./read-logs-of-version.sh ${V} ${CRASH_LOG_ROOT} ${DUMP_FILE_ROOT} ${SYMBOL_ROOT}
