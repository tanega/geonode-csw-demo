"""
Bridge CSW catalog <-> cloud-native assets (step 6): register the MinIO
COG/GeoParquet objects and their titiler/duckdb-api endpoints as
geonode.base.models.Link rows on the matching Dataset, so pycsw's
ResourceBase.download_links property (queried live from link_set on every
GetRecords call, see geonode/base/models.py) surfaces them as extra
dct:references entries. No Dataset.save() needed: download_links() is
computed at request time, not cached.

Idempotent (get_or_create on resource+url) — safe to re-run after a fresh
`importlayers` + step 3/4 setup.

Run:
docker cp data/scripts/link_cloud_native_assets.py \
  geonode-demo-django-1:/tmp/link_cloud_native_assets.py
docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py shell < /tmp/link_cloud_native_assets.py"
"""

from geonode.base.models import Link
from geonode.layers.models import Dataset

SITEURL = "http://geonode.localhost"

LINKS = [
    (
        "lisbon_elevation",
        [
            dict(
                # No comma in `name`: for link_type="data" (and "image"/
                # "original"), ResourceBase.download_links() interpolates
                # `name` into pycsw's legacy CSV-style link serialization
                # (name,description,protocol,url joined by "^"/","), which
                # naively splits on commas — one in `name` shifts every
                # field after it and corrupts the CSW dct:references output.
                # (link_type="html" below is unaffected: its description is
                # a hardcoded "Web address (URL)", not link.name.)
                name="Cloud-Optimized GeoTIFF (COG) on MinIO",
                extension="tif",
                mime="image/tiff",
                link_type="data",
                url="http://minio.geonode.localhost/geonode-demo/cog/lisbon_elevation_cog.tif",
            ),
            dict(
                name="Cloud-native preview (TiTiler, dynamic tiles from COG)",
                extension="html",
                mime="text/html",
                link_type="html",
                url=(
                    f"{SITEURL}/titiler/cog/preview.png?"
                    "url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif"
                ),
            ),
        ],
    ),
    (
        "ne_110m_admin_0_countries",
        [
            dict(
                name="GeoParquet (MinIO)",
                extension="parquet",
                mime="application/vnd.apache.parquet",
                link_type="data",
                url="http://minio.geonode.localhost/geonode-demo/geoparquet/ne_110m_admin_0_countries.parquet",
            ),
            dict(
                name="Cloud-native analytics (DuckDB spatial queries over GeoParquet)",
                extension="html",
                mime="text/html",
                link_type="html",
                url=f"{SITEURL}/analytics/countries",
            ),
        ],
    ),
]

for dataset_name, links in LINKS:
    dataset = Dataset.objects.get(name=dataset_name)
    for link in links:
        obj, created = Link.objects.get_or_create(
            resource=dataset.resourcebase_ptr,
            url=link["url"],
            defaults=dict(
                name=link["name"],
                extension=link["extension"],
                mime=link["mime"],
                link_type=link["link_type"],
            ),
        )
        print(f"{'created' if created else 'exists'}: {dataset_name} -> {link['url']}")
