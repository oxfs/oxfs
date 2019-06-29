#!/bin/bash

REMOTE_HOST=$1
REMOTE_USER=$2
REMOTE_PATH=$3
TEST_PATH=$4
TEST_LOOP=$5

mkdir -p $TEST_PATH
sudo rm -rf /tmp/oxfs
sudo oxfs -s $REMOTE_USER@$REMOTE_HOST -m $TEST_PATH -r $REMOTE_PATH -p /tmp/oxfs &
sleep 10

echo "Start to oxfs test."
START=$(date +%s)

./files-ops.sh $TEST_PATH $TEST_LOOP > /dev/null 2>&1
# ./files-ops.sh $TEST_PATH $TEST_LOOP

END=$(date +%s)
DIFF=$(( $END - $START ))
echo "oxfs took $DIFF seconds"

sudo pkill oxfs
