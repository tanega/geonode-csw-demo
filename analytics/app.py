import os

import duckdb
from fastapi import FastAPI, HTTPException, Query

MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
MINIO_BUCKET = os.environ["MINIO_BUCKET"]
COUNTRIES_KEY = os.environ.get(
    "COUNTRIES_PARQUET_KEY", "geoparquet/ne_110m_admin_0_countries.parquet"
)
COUNTRIES_URL = f"s3://{MINIO_BUCKET}/{COUNTRIES_KEY}"

app = FastAPI(title="geonode-demo — DuckDB analytics")


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
