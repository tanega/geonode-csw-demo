#!/usr/bin/env bash
# Upload a local file to the MinIO bucket, via a throwaway `mc` container on
# the compose network (host has no direct route to MinIO: no host port is
# published, see docker-compose.yml).
# Usage: upload_minio.sh <local-file> <bucket-relative-key>
# Example: upload_minio.sh data/processed/foo_cog.tif cog/foo_cog.tif
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <local-file> <bucket-relative-key>" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
# Extract only the vars we need instead of `source`-ing .env: some upstream
# GeoNode/GeoServer values there are unquoted multi-word strings (e.g.
# GEOSERVER_JAVA_OPTS) that a plain `source` can't parse safely.
MINIO_ROOT_USER="$(grep -E '^MINIO_ROOT_USER=' "$repo_root/.env" | cut -d= -f2-)"
MINIO_ROOT_PASSWORD="$(grep -E '^MINIO_ROOT_PASSWORD=' "$repo_root/.env" | cut -d= -f2-)"
MINIO_BUCKET="$(grep -E '^MINIO_BUCKET=' "$repo_root/.env" | cut -d= -f2-)"

local_file="$1"
key="$2"
network="${COMPOSE_PROJECT_NAME:-geonode-demo}_geonode-net"
abs_dir="$(cd "$(dirname "$local_file")" && pwd)"
filename="$(basename "$local_file")"

docker run --rm --entrypoint sh \
  -v "$abs_dir:/upload:ro" \
  --network "$network" \
  minio/mc:latest -c "
mc alias set localminio http://minio:9000 '$MINIO_ROOT_USER' '$MINIO_ROOT_PASSWORD' >/dev/null &&
mc mb -p localminio/$MINIO_BUCKET >/dev/null 2>&1 || true
mc cp /upload/$filename localminio/$MINIO_BUCKET/$key
"
