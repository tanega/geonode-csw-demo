# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Learning project implementing OGC CSW-based spatial data discovery via GeoNode, with a hybrid storage stack and a plan to build a standalone external frontend consuming GeoNode's OGC endpoints (frontend structure/libraries are a deliberately separate, not-yet-started phase — see `docs/architecture.md`).

There is no application code yet: this repo is currently pure infrastructure (docker-compose stack + docs). Nothing to build/lint/test in the traditional sense.

## Commands

```bash
cp .env.example .env                                  # fill in real secrets first
docker compose up -d db redis                          # wait ~10s for DB init (creates both DB roles)
docker compose up -d django celery geoserver traefik    # ~2-3 min: migrations, prepare, fixtures, uwsgi
docker compose logs -f django                           # watch startup
docker compose ps -a                                     # check container status
```

CSW verification (see "Traefik is broken" below for why this bypasses port 80):

```bash
docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities"

docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&elementSetName=full&resultType=results"
```

`elementSetName` is mandatory on GetRecords or pycsw returns a `MissingParameterValue` exception.

Importing a dataset (also goes through django, not Traefik):

```bash
docker cp <file> geonode-demo-django-1:/data/
docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py importlayers /data/<file> -u admin -p <GEONODE_ADMIN_PASSWORD> -hh http://django:8000"
```

Plain GeoJSON is rejected by the importer ("No handlers found for this dataset type/action"). Convert to GeoPackage first, and force uniform multi-geometries if the source mixes POLYGON/MULTIPOLYGON (GeoNode's importer rejects mixed `GEOMETRY` columns too):

```bash
ogr2ogr -f GPKG -nlt MULTIPOLYGON -nlt PROMOTE_TO_MULTI out.gpkg in.geojson
```

To debug a django crash that produces no output in `docker logs`: check `invoke.log` inside the container — `entrypoint.sh` pipes each `invoke <task>` step's output there instead of stdout, and only prints `"<task> tasks done"` on success (silent exit on failure otherwise):

```bash
docker cp geonode-demo-django-1:/usr/src/geonode/invoke.log /tmp/invoke.log
```

## Architecture

Hybrid storage, decided deliberately despite the two-stacks overhead (see `docs/architecture.md` "Décisions actées"):

- **GeoServer** (via GeoNode) — canonical OGC stack: WMS/WFS/WCS, plus CSW (pycsw, bundled inside the django app, not a separate service) for discovery. This is the source of truth for OGC compliance.
- **MinIO + DuckDB + TiTiler** — secondary cloud-native layer for fast analytics/previews: vector as GeoParquet (queried via DuckDB), raster as COG (tiled via TiTiler). Not yet wired to CSW metadata — bridging cloud-native assets into the catalog is an open step (#6 in `docs/architecture.md`).
- **Traefik**, not nginx, is the single reverse proxy in front of everything (GeoNode's own bundled nginx/letsencrypt services are intentionally dropped).

`docker-compose.yml` follows GeoNode's official upstream compose/`.env.sample` (django/celery/geoserver/db/redis), with `x-geonode-env`/`x-geonode-volumes` YAML anchors sharing config between `django` and `celery` (they're the same image, different `command`/`IS_CELERY`).

### Known gaps vs. the official GeoNode stack (all fixed here, see `docs/step2-geonode-csw.md` for the full incident writeup)

These were not obvious from upstream docs and cost real debugging time — worth knowing before touching `docker-compose.yml`:

- `django`/`celery` need an explicit `entrypoint: ["/usr/src/geonode/entrypoint.sh"]` + `command`. Without it the container just runs bare bash and exits immediately with no error.
- GeoNode needs **two separate Postgres roles/DBs**: `GEONODE_DATABASE*` (app metadata) and `GEONODE_GEODATABASE*` (GeoServer's vector datastore). The `geonode/postgis` image creates both natively from those env vars alone — no custom init script needed.
- `geoserver` needs `GEOSERVER_JAVA_OPTS` explicitly set or the JVM fails to start with a cryptic `Could not find or load main class XX:ParallelGCThreads=4` error.
- `django`/`celery` need `OAUTH2_CLIENT_ID`/`OAUTH2_CLIENT_SECRET` or the `invoke prepare` startup step throws `KeyError` and the container exits — silently, since `invoke`'s output goes to `invoke.log`, not `docker logs`.

### Traefik is currently broken in this dev environment

Traefik can't read the mounted docker socket (`Error response from daemon: ` in a retry loop, no routers ever register) — most likely Docker Desktop's **Enhanced Container Isolation** blocking socket access from containers. Not fixable from `docker-compose.yml` alone; needs a Docker Desktop settings change (or a `docker-socket-proxy`). Until resolved, everything (CSW checks, dataset imports) talks to `django` directly over the internal docker network (`docker exec ... -H "Host: django" http://localhost:8000/...` or `-hh http://django:8000` for management commands) instead of through port 80.

### Project stage tracking

`docs/architecture.md` lists the 9 planned steps and which are done; `docs/step2-geonode-csw.md` is the detailed log for step 2 specifically (GeoNode + CSW deployment — done). Check both before assuming what's implemented vs. planned.
