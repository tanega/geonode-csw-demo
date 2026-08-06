import logging
import os
import subprocess
import tempfile
from urllib.parse import urlparse

import boto3
import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

DUCKDB_API_BASE = os.environ.get("DUCKDB_API_BASE", "http://duckdb-api:8000")


def _geodatabase_pg_conn_string():
    parsed = urlparse(os.environ["GEODATABASE_URL"].replace("postgis://", "postgresql://", 1))
    return (
        f"dbname={parsed.path.lstrip('/')} host={parsed.hostname} "
        f"port={parsed.port or 5432} user={parsed.username} password={parsed.password}"
    )


def _minio_public_url(key):
    domain = urlparse(settings.SITEURL).hostname
    bucket = os.environ["MINIO_BUCKET"]
    return f"http://minio.{domain}/{bucket}/{key}"


def _upload_to_minio(local_path, key):
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{os.environ.get('MINIO_ENDPOINT', 'minio:9000')}",
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    )
    client.upload_file(local_path, os.environ["MINIO_BUCKET"], key)


@shared_task(ignore_result=True)
def mirror_dataset_to_geoparquet(dataset_id):
    """
    Best-effort: the GeoServer-side import already succeeded by the time
    this runs (triggered from Dataset post_save), so a failure here
    should not surface as an upload failure to the user.

    GDAL in this container has no Arrow/Parquet support (see
    analytics/app.py), so the PostGIS table is exported to GPKG locally
    (GDAL's PG + GPKG drivers are both present — GeoNode's own importer
    already relies on them) and handed to duckdb-api for the GPKG->Parquet
    step, which uses DuckDB's native Parquet writer instead of GDAL.
    """
    from geonode.base.models import Link
    from geonode.layers.models import Dataset

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return

    if dataset.subtype != "vector":
        return

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = os.path.join(tmpdir, f"{dataset.name}.gpkg")
            result = subprocess.run(
                [
                    "ogr2ogr",
                    "-f",
                    "GPKG",
                    gpkg_path,
                    f"PG:{_geodatabase_pg_conn_string()}",
                    dataset.name,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("GeoParquet mirror: PostGIS->GPKG export failed for %s: %s", dataset.name, result.stderr)
                return

            with open(gpkg_path, "rb") as gpkg_file:
                convert_response = requests.post(
                    f"{DUCKDB_API_BASE}/convert/to-parquet",
                    files={"file": (f"{dataset.name}.gpkg", gpkg_file, "application/geopackage+sqlite3")},
                )
            if not convert_response.ok:
                logger.error("GeoParquet mirror: GPKG->Parquet conversion failed for %s: %s", dataset.name, convert_response.text)
                return

            parquet_path = os.path.join(tmpdir, f"{dataset.name}.parquet")
            with open(parquet_path, "wb") as f:
                f.write(convert_response.content)

            key = f"geoparquet/{dataset.name}.parquet"
            _upload_to_minio(parquet_path, key)

        Link.objects.get_or_create(
            resource=dataset.resourcebase_ptr,
            url=_minio_public_url(key),
            defaults=dict(
                name="GeoParquet (cloud-native mirror, MinIO)",
                extension="parquet",
                mime="application/vnd.apache.parquet",
                link_type="data",
            ),
        )
    except Exception:
        logger.exception("GeoParquet mirror failed for dataset %s", dataset_id)
