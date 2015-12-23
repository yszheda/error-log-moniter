#!/bin/bash

V=$1
CRASH_LOG_ROOT=$2
DUMP_FILE_ROOT=$3
SYMBOL_ROOT=$4

CRASH_LOG_PATH="${CRASH_LOG_ROOT}/${V}"
find ${CRASH_LOG_PATH} -type f -exec basename {} \; | sed 's/\.dmp//g' | xargs -I % ./read-crash-log.sh ${V} % ${CRASH_LOG_ROOT} ${DUMP_FILE_ROOT} ${SYMBOL_ROOT}
