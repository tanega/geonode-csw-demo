import os
import tempfile

import duckdb
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
MINIO_BUCKET = os.environ["MINIO_BUCKET"]
COUNTRIES_KEY = os.environ.get(
    "COUNTRIES_PARQUET_KEY", "geoparquet/ne_110m_admin_0_countries.parquet"
)
COUNTRIES_URL = f"s3://{MINIO_BUCKET}/{COUNTRIES_KEY}"

app = FastAPI(title="geonode-demo — DuckDB analytics")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)


def get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}'")
    con.execute(f"SET s3_access_key_id='{MINIO_ROOT_USER}'")
    con.execute(f"SET s3_secret_access_key='{MINIO_ROOT_PASSWORD}'")
    con.execute("SET s3_use_ssl=false")
    con.execute("SET s3_url_style='path'")
    return con


# One shared in-memory connection: cheap to create, but re-registering the
# httpfs/spatial extensions on every request adds latency for no benefit in
# this single-worker demo service.
_con = get_connection()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/countries")
def list_countries(limit: int = Query(default=10, ge=1, le=177)):
    rows = _con.execute(
        f"""
        SELECT
            "ADMIN" AS admin,
            "ADM0_A3" AS adm0_a3,
            "CONTINENT" AS continent,
            ST_Area(geometry) AS area_deg2
        FROM read_parquet('{COUNTRIES_URL}')
        ORDER BY area_deg2 DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    columns = ["admin", "adm0_a3", "continent", "area_deg2"]
    return [dict(zip(columns, row)) for row in rows]


@app.get("/countries/{adm0_a3}")
def get_country(adm0_a3: str):
    row = _con.execute(
        f"""
        SELECT
            "ADMIN" AS admin,
            "ADM0_A3" AS adm0_a3,
            "CONTINENT" AS continent,
            ST_Area(geometry) AS area_deg2,
            ST_AsText(ST_Centroid(geometry)) AS centroid
        FROM read_parquet('{COUNTRIES_URL}')
        WHERE "ADM0_A3" = ?
        """,
        [adm0_a3.upper()],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown adm0_a3 {adm0_a3!r}")
    columns = ["admin", "adm0_a3", "continent", "area_deg2", "centroid"]
    return dict(zip(columns, row))


# --- Format conversion, used internally by geonode-custom/uploads_api ---
#
# GDAL in the django/celery containers (bundled with the upstream
# geonode/geonode image) isn't built with Arrow/Parquet support, so it
# can't read or write GeoParquet at all (verified: `ogr2ogr --formats`
# there doesn't list Parquet). DuckDB's spatial extension doesn't have
# that limitation: it reads Parquet natively (no GDAL involved) and can
# write GDAL-supported formats like GPKG via `COPY ... (FORMAT GDAL)`, and
# the reverse (`ST_Read` any GDAL vector format, write native Parquet).
# These two endpoints exist purely so django/celery can offload the
# conversion here instead of needing GDAL's Parquet driver themselves.


def _promoted_geometry_type(con, select_expr, source_sql, geom_col):
    """
    DuckDB's GDAL export always declares a generic "GEOMETRY" column type
    in the output's schema, regardless of what's actually in the data —
    GeoNode's importer rejects that mismatch (expects a concrete type,
    same as any normal GPKG export would have). Compute the concrete type
    the caller should force via ogr2ogr -nlt: promote to the Multi* form
    unless it's Point data, mirroring GeoNode's own gpkg handler logic
    (geonode/upload/handlers/common/vector.py — skips promotion only for
    Point).
    """
    families = {
        row[0].upper().removeprefix("MULTI")
        for row in con.execute(
            f'SELECT DISTINCT ST_GeometryType("{geom_col}") FROM ({source_sql}) AS s'
        ).fetchall()
    }
    if len(families) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Mixed incompatible geometry families found: {sorted(families)}",
        )
    family = families.pop()
    return family if family == "POINT" else f"MULTI{family}"


@app.post("/convert/to-gpkg")
async def convert_parquet_to_gpkg(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "input.parquet")
        with open(src_path, "wb") as f:
            f.write(await file.read())

        con = duckdb.connect(database=":memory:")
        con.execute("LOAD spatial")

        # GeoParquet's optional per-row bbox "covering" column is a STRUCT,
        # a type GDAL's OGR layer model has no equivalent for — drop it,
        # it's a read-optimization column anyway, not source data.
        described = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{src_path}')"
        ).fetchall()
        struct_cols = [row[0] for row in described if row[1].upper().startswith("STRUCT")]
        select_expr = f"* EXCLUDE ({', '.join(struct_cols)})" if struct_cols else "*"
        geom_col = next(row[0] for row in described if row[1].upper() == "GEOMETRY")

        source_sql = f"SELECT {select_expr} FROM read_parquet('{src_path}')"
        geometry_type = _promoted_geometry_type(con, select_expr, source_sql, geom_col)

        out_path = os.path.join(tmpdir, "output.gpkg")
        try:
            # GeoParquet's CRS is recorded in file-level metadata that
            # DuckDB's parquet reader doesn't surface as a usable SRS here;
            # assumes EPSG:4326, the GeoParquet spec's default and the
            # overwhelmingly common case (same assumption GeoJSON's own
            # spec makes).
            con.execute(
                f"COPY ({source_sql}) TO '{out_path}' "
                f"WITH (FORMAT GDAL, DRIVER 'GPKG', SRS 'EPSG:4326')"
            )
        except duckdb.Error as e:
            raise HTTPException(status_code=400, detail=f"Conversion to GeoPackage failed: {e}")

        with open(out_path, "rb") as f:
            data = f.read()

    return Response(
        content=data,
        media_type="application/geopackage+sqlite3",
        headers={"X-Geometry-Type": geometry_type},
    )


@app.post("/convert/to-parquet")
async def convert_gpkg_to_parquet(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "input.gpkg")
        with open(src_path, "wb") as f:
            f.write(await file.read())

        con = duckdb.connect(database=":memory:")
        con.execute("LOAD spatial")

        out_path = os.path.join(tmpdir, "output.parquet")
        try:
            con.execute(
                f"COPY (SELECT * FROM ST_Read('{src_path}')) TO '{out_path}' (FORMAT PARQUET)"
            )
        except duckdb.Error as e:
            raise HTTPException(status_code=400, detail=f"Conversion to GeoParquet failed: {e}")

        with open(out_path, "rb") as f:
            data = f.read()

    return Response(content=data, media_type="application/vnd.apache.parquet")
