#!/bin/bash

TEST_PATH=$1
LOOP=$2

# basic ops

cd $TEST_PATH
rm -rf foo
for x in $(seq 1 $LOOP);
do

    mkdir -p foo
    cd foo
    ls -lrt
    for i in $(seq 1 10);
    do
        echo "foo" >> txt
        ls -lrt
        cat txt
    done

    cd ..
    ls -lrt

    # mkdir -p project
    # cd project
    # git init
    # echo "fooooooo" > testfile
    # git status
    # git status
    # git add .
    # git commit -m "foooo"
    # git status
    # git checkout -b develop
    # git status
    # cd ..

done
