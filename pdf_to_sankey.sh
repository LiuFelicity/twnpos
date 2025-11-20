#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_pdf>"
    exit 1
fi

set -e

python3 doc_summary.py "$1" report.csv
python3 create_sankey.py report.csv
rm -f report.csv
python3 -m http.server -d result 8000