import logging
import os
import subprocess
import tempfile

import requests
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from geonode.base.api.permissions import IsOwnerOrAdmin
from geonode.base.models import Link, ResourceBase

logger = logging.getLogger(__name__)

PARQUET_EXTENSIONS = (".parquet", ".geoparquet")
DUCKDB_API_BASE = os.environ.get("DUCKDB_API_BASE", "http://duckdb-api:8000")


class ConvertParquetView(APIView):
    """
    GeoNode's importer has no handler for GeoParquet, and GDAL in this
    image isn't built with Arrow/Parquet support either (see
    analytics/app.py's convert endpoints for why). Offloads the
    parquet->gpkg conversion to the existing duckdb-api service, then
    forwards the result to the real importer endpoint so the rest of the
    import flow (validation, PostGIS load, GeoServer publish) is
    unchanged.
    """

    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        upload = request.FILES.get("base_file")
        if not upload:
            raise ValidationError("base_file is required")

        if not upload.name.lower().endswith(PARQUET_EXTENSIONS):
            raise ValidationError("base_file must be a .parquet/.geoparquet file")

        convert_response = requests.post(
            f"{DUCKDB_API_BASE}/convert/to-gpkg",
            files={"file": (upload.name, upload, "application/vnd.apache.parquet")},
        )
        if not convert_response.ok:
            logger.error("duckdb-api parquet->gpkg conversion failed: %s", convert_response.text)
            raise ValidationError(f"Conversion to GeoPackage failed: {convert_response.text[:500]}")

        # DuckDB's GDAL writer always declares a generic "GEOMETRY" column
        # type in gpkg_geometry_columns regardless of what it actually
        # wrote -- GeoNode's importer rejects that mismatch. duckdb-api
        # computes the real concrete type from the data itself (it has to:
        # ogr2ogr can't infer it either once the source already claims
        # "Unknown/GEOMETRY" -- verified empirically, -nlt PROMOTE_TO_MULTI
        # is a no-op in that case) and returns it via this header.
        geometry_type = convert_response.headers.get("X-Geometry-Type")
        if not geometry_type:
            raise ValidationError("duckdb-api did not return a geometry type")

        title = os.path.splitext(upload.name)[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_gpkg_path = os.path.join(tmpdir, "raw.gpkg")
            with open(raw_gpkg_path, "wb") as f:
                f.write(convert_response.content)

            # Re-write through ogr2ogr (GPKG->GPKG, no Parquet involved,
            # so this container's GDAL handles it fine) forcing the real
            # type, so the output declares a concrete type like any
            # normal GPKG upload would have.
            final_gpkg_path = os.path.join(tmpdir, "final.gpkg")
            result = subprocess.run(
                ["ogr2ogr", "-f", "GPKG", "-nlt", geometry_type, final_gpkg_path, raw_gpkg_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("gpkg normalization failed: %s", result.stderr)
                raise ValidationError(f"GeoPackage normalization failed: {result.stderr[-500:]}")

            with open(final_gpkg_path, "rb") as gpkg_file:
                response = requests.post(
                    # "django" (not "localhost") -- matches importlayers.py's
                    # own internal call (-hh http://django:8000);
                    # ALLOWED_HOSTS (docker-compose.yml x-geonode-env)
                    # doesn't include "localhost".
                    "http://django:8000/api/v2/uploads/upload/",
                    headers={"Authorization": request.headers.get("Authorization", "")},
                    files={
                        "base_file": (
                            f"{title}.gpkg",
                            gpkg_file,
                            "application/geopackage+sqlite3",
                        )
                    },
                )

        return Response(data=response.json(), status=response.status_code)


class SourceLinkView(APIView):
    """
    Records a contributor-supplied "source" URL for a resource as a
    `Link` (link_type="metadata") -- the same mechanism the GeoParquet
    auto-mirror uses (see signals.py, docs/step6-catalog-bridge.md), so
    it shows up in CSW GetRecords `dct:references` for free. No public
    GeoNode API creates Links directly: ResourceBaseSerializer's `links`
    field is read-only.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request):
        resource_id = request.data.get("resource")
        url = request.data.get("url")
        if not resource_id or not url:
            raise ValidationError("resource and url are required")

        resource = get_object_or_404(ResourceBase, pk=resource_id)
        self.check_object_permissions(request, resource)

        try:
            URLValidator()(url)
        except DjangoValidationError:
            raise ValidationError("url must be a valid URL")

        link, _ = Link.objects.update_or_create(
            resource=resource,
            link_type="metadata",
            name="Source",
            defaults={"url": url, "extension": "", "mime": "text/html"},
        )
        return Response({"id": link.id, "url": link.url}, status=201)
