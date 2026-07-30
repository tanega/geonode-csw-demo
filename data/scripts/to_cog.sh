#!/usr/bin/env bash
# Convert a raster to Cloud Optimized GeoTIFF (COG).
# Usage: to_cog.sh <input-raster> <output-cog.tif>
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <input-raster> <output-cog.tif>" >&2
  exit 1
fi

in="$1"
out="$2"

gdal_translate "$in" "$out" \
  -of COG \
  -co COMPRESS=DEFLATE \
  -co OVERVIEWS=AUTO

gdalinfo "$out" | grep -i "LAYOUT\|Overviews"
