#!/bin/bash

V=$1
FILE_NAME=$2
CRASH_LOG_ROOT=$3
DUMP_FILE_ROOT=$4
SYMBOL_ROOT=$5

CRASH_LOG_PATH="${CRASH_LOG_ROOT}/${V}"
if [ ! -d "$CRASH_LOG_PATH" ]; then
		exit
fi

DUMP_FILE_PATH="${DUMP_FILE_ROOT}/${V}"
if [ ! -d "${DUMP_FILE_PATH}" ]; then
		mkdir -p "${DUMP_FILE_PATH}"
fi

LOG_FILE="${CRASH_LOG_PATH}/${FILE_NAME}.dmp"
DUMP_FILE="${DUMP_FILE_PATH}/${FILE_NAME}.dump"

minidump_stackwalk ${LOG_FILE} ${SYMBOL_ROOT} > ${DUMP_FILE}
