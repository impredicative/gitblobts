#!/usr/bin/env bash

cd ./requirements
pip-compile -o ./install.txt ./install.in >/dev/null
pip-compile -o ./rtd.txt ./*.in >/dev/null
