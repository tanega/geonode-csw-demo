import logging
import os
import subprocess
import tempfile
from urllib.parse import urlparse

import boto3
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


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
            parquet_path = os.path.join(tmpdir, f"{dataset.name}.parquet")
            result = subprocess.run(
                [
                    "ogr2ogr",
                    "-f",
                    "Parquet",
                    parquet_path,
                    f"PG:{_geodatabase_pg_conn_string()}",
                    dataset.name,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("GeoParquet mirror failed for %s: %s", dataset.name, result.stderr)
                return

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
