#!/bin/bash

REMOTE_HOST=$1
REMOTE_USER=$2
REMOTE_PATH=$3
TEST_PATH=$4
TEST_LOOP=$5

mkdir -p $TEST_PATH
sshfs $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH $TEST_PATH

echo "Start to sshfs test."
START=$(date +%s)

./files-ops.sh $TEST_PATH $TEST_LOOP > /dev/null 2>&1

END=$(date +%s)
DIFF=$(( $END - $START ))
echo "sshfs took $DIFF seconds"

sudo umount $TEST_PATH
