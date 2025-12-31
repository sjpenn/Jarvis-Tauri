#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd):/Users/sjpenn/Library/Python/3.9/lib/python/site-packages
python3 -m jarvis.cli ui "$@"
