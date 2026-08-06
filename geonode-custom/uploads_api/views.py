import logging
import os
import subprocess
import tempfile

import requests
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

PARQUET_EXTENSIONS = (".parquet", ".geoparquet")


class ConvertParquetView(APIView):
    """
    GeoNode's importer has no handler for GeoParquet (no PostGIS-backed
    format matches it — see docs/architecture.md's hybrid-storage
    decision). Converts to GeoPackage with ogr2ogr, then forwards to the
    real importer endpoint so the rest of the import flow (validation,
    PostGIS load, GeoServer publish) is unchanged.
    """

    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        upload = request.FILES.get("base_file")
        if not upload:
            raise ValidationError("base_file is required")

        if not upload.name.lower().endswith(PARQUET_EXTENSIONS):
            raise ValidationError("base_file must be a .parquet/.geoparquet file")

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, upload.name)
            with open(src_path, "wb") as f:
                for chunk in upload.chunks():
                    f.write(chunk)

            gpkg_path = os.path.join(tmpdir, "converted.gpkg")
            result = subprocess.run(
                [
                    "ogr2ogr",
                    "-f",
                    "GPKG",
                    "-nlt",
                    "PROMOTE_TO_MULTI",
                    gpkg_path,
                    src_path,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("ogr2ogr parquet->gpkg failed: %s", result.stderr)
                raise ValidationError(f"Conversion to GeoPackage failed: {result.stderr[-500:]}")

            title = os.path.splitext(upload.name)[0]
            with open(gpkg_path, "rb") as gpkg_file:
                response = requests.post(
                    "http://localhost:8000/api/v2/uploads/upload/",
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
