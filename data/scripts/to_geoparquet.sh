#!/usr/bin/env bash
# Convert a vector dataset to GeoParquet.
# Usage: to_geoparquet.sh <input-vector> <output.parquet>
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <input-vector> <output.parquet>" >&2
  exit 1
fi

in="$1"
out="$2"

ogr2ogr -f Parquet "$out" "$in"

gpq describe "$out"
