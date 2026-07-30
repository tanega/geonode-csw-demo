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
docker compose up -d web                                # frontend (needs WEB_OAUTH_CLIENT_ID in .env, see below)
docker compose logs -f django                           # watch startup
docker compose ps -a                                     # check container status
```

Frontend (`web` service) is served by Traefik at `http://www.localhost` —
add `127.0.0.1 www.localhost` to `/etc/hosts` (doesn't auto-resolve on
macOS the way some `.localhost` names do). `WEB_OAUTH_CLIENT_ID` in `.env`
must come from `data/scripts/create_frontend_oauth_app.py` (see
`docs/iam-option-a-login.md`) — Vite bakes it into the static bundle at
*build* time, so `docker compose build web` must be re-run after changing
it (a running-container env var change has no effect).

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

### web (frontend) container needs a real Node.js alongside bun

`web/Dockerfile` builds with `oven/bun:1`, but `vue-tsc --build` (part of
`bun run build`) failed inside the container with `TS2307: Cannot find
module '*.vue'` for every single `.vue` import, while `bun run type-check`
passed fine on the host. Root cause: `vue-tsc`'s `#!/usr/bin/env node`
shebang needs a genuine Node.js — in the bun image `node` is just a symlink
back to bun's own Node-compat shim (`/usr/local/bun-node-fallback-bin/node
-> bun`), which doesn't support vue-tsc's `.vue` module-resolution
patching. The host has a real Node.js on `PATH` (e.g. via nvm/pyenv), so it
worked there and only broke in the container. Fixed by installing real
`nodejs` via `apt-get` in the build stage before `bun install`/`bun run
build`. If this resurfaces (e.g. switching base images), check `which node`
inside the container isn't pointing back at bun.

### Traefik was broken — fixed by pinning a newer image tag

Traefik used to fail reading the docker socket (`Error response from daemon: ` in a retry loop, no routers ever registered). Root cause: `traefik:v3.0` (built July 2024) bundles a docker-client library that negotiates/defaults to a Docker API version below this machine's Docker Desktop engine minimum (`MinAPIVersion` 1.40, Docker Desktop 4.80 / Engine 29.6.1). Every provider call to the daemon got a 400, and traefik's error-unwrap drops the daemon's message text, producing the misleading empty `Error response from daemon: `. It was **not** Enhanced Container Isolation (Business/Enterprise-only, not applicable on this install) and **not** a socket-path/permissions problem — both were verified fine (`/var/run/docker.sock` symlink and mount are correct).

Fix: pin `image: traefik:v3.7.9` for the `traefik` service — routers now register correctly. Verify with:
```bash
curl -s http://localhost:${TRAEFIK_DASHBOARD_PORT:-8080}/api/http/routers
```
`titiler` and `duckdb-api` also needed explicit `traefik.http.services.<name>.loadbalancer.server.port` labels (`80` and `8000` respectively) — traefik can't infer the container port when the image declares no `EXPOSE`.

If this recurs after a future Docker Desktop update: compare `docker version --format '{{.Server.APIVersion}}'` against what the pinned traefik tag's bundled docker-client supports, and bump the traefik tag first — don't re-chase socket/isolation settings.

The CSW verification and import commands below still bypass Traefik/port 80 and talk to `django` directly over the internal docker network; that path remains the documented/tested one, since routing through Traefik on port 80 (which needs `DOMAIN`/hosts setup) hasn't been exercised end-to-end yet.

### Project stage tracking

`docs/architecture.md` lists the 9 planned steps and which are done; `docs/step2-geonode-csw.md` is the detailed log for step 2 specifically (GeoNode + CSW deployment — done). Check both before assuming what's implemented vs. planned.
