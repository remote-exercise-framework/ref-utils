#!/bin/bash

sudo python3 -m pip install -U pip setuptools wheel
sudo python3 setup.py sdist
sudo python3 setup.py sdist