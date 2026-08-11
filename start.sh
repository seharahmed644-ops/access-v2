#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
cat server_parts/01.py server_parts/02.py server_parts/03.py > server.py
python3 server.py
