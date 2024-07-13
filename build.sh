#!/usr/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"
python3 -m PyInstaller build.spec
