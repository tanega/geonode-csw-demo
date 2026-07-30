# Étape 4 — Couche analytics/preview (DuckDB + TiTiler)

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

Cette étape branche TiTiler et un petit service DuckDB sur les objets MinIO
produits à l'[étape 3](step3-cloud-native-storage.md) (COG et GeoParquet).

## TiTiler → COG sur MinIO

`titiler` (déjà scaffoldé, jamais démarré) reçoit les variables d'env S3/GDAL
nécessaires pour lire un COG directement depuis MinIO via le driver
`/vsis3/`:

```yaml
AWS_S3_ENDPOINT: "minio:9000"
AWS_HTTPS: "NO"
AWS_VIRTUAL_HOSTING: "FALSE"
AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
GDAL_DISABLE_READDIR_ON_OPEN: "EMPTY_DIR"
```

Pas de port host publié (même limitation Traefik qu'aux étapes précédentes)
— vérifié via un conteneur `curl` jetable sur `geonode-net`:

```bash
docker run --rm --network geonode-demo_geonode-net curlimages/curl:latest -s \
  "http://titiler:80/cog/info?url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif"

docker run --rm --network geonode-demo_geonode-net curlimages/curl:latest -s -o preview.png \
  "http://titiler:80/cog/preview.png?url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif"
```

`/cog/info` répond 200 avec les bounds/CRS/bandes du COG uploadé à l'étape 3;
`/cog/preview.png` répond 200 `image/png`. La même URL `s3://...` peut servir
aux endpoints `/cog/tiles/{z}/{x}/{y}` pour un usage XYZ classique.

## DuckDB → GeoParquet sur MinIO (`analytics/`)

Pas de service DuckDB officiel — comme prévu dans `architecture.md`, un petit
wrapper FastAPI (`analytics/app.py`, `analytics/Dockerfile`) l'expose:

- charge les extensions `httpfs` (accès S3) et `spatial` (types/fonctions
  géo) au démarrage ;
- pointe `httpfs` vers MinIO via `s3_endpoint`/`s3_access_key_id`/
  `s3_secret_access_key`/`s3_url_style='path'` (mêmes identifiants que le
  reste de la stack, lus depuis les variables d'env du service) ;
- lit le GeoParquet de l'étape 3 avec `read_parquet('s3://...')` — la colonne
  géométrie est déjà typée `GEOMETRY` nativement par l'extension spatial
  (métadonnées GeoParquet auto-détectées), pas besoin de `ST_GeomFromWKB`.

Volontairement **pas** d'endpoint `/query?sql=...` générique (équivalent à
de l'injection SQL par design, même pour un projet d'apprentissage non
exposé) — 3 endpoints dédiés à la place:

- `GET /health`
- `GET /countries?limit=N` — top N pays par aire (`ST_Area`), triés
  décroissant
- `GET /countries/{adm0_a3}` — un pays (aire + centroïde `ST_Centroid`/
  `ST_AsText`), 404 si code inconnu

`area_deg2`/le centroïde sont calculés directement en EPSG:4326 (CRS du
GeoParquet source) — utiles pour comparer des ordres de grandeur entre pays
dans ce jeu de test, pas une aire métrique réelle (pas de reprojection en
CRS équal-area).

Vérifié via le même conteneur `curl` jetable:

```bash
docker run --rm --network geonode-demo_geonode-net curlimages/curl:latest -s \
  "http://duckdb-api:8000/countries?limit=3"
docker run --rm --network geonode-demo_geonode-net curlimages/curl:latest -s \
  "http://duckdb-api:8000/countries/PRT"
```

Résultats observés: top 3 = Antarctica, Russia, Canada (cohérent); `PRT` →
`{"admin":"Portugal","adm0_a3":"PRT","continent":"Europe","area_deg2":9.80,"centroid":"POINT (-8.0558 39.6340)"}`.

## Démarrage

```bash
docker compose up -d minio                     # si pas déjà démarré (étape 3)
docker compose up -d --build titiler duckdb-api
```

`duckdb-api` a un `build:` (image locale `analytics/Dockerfile`) — nécessite
`--build` au premier démarrage ou après modification de `analytics/`.

## Critère de sortie de l'étape

- [x] `titiler` lit un COG stocké dans MinIO (`/cog/info`, `/cog/preview.png`
      répondent 200)
- [x] Service DuckDB (wrapper FastAPI) répond, extensions `httpfs`+`spatial`
      chargées, lit le GeoParquet stocké dans MinIO
- [x] Au moins une requête spatiale (`ST_Area`, `ST_Centroid`) validée sur le
      jeu de test

## Reste à faire avant l'étape 5+

- Étape 6 (pont catalogage): ni le COG ni le GeoParquet ne sont référencés
  dans le catalogue CSW pycsw — ces deux couches restent des îlots
  indépendants du catalogue OGC pour l'instant.
- Limitation Traefik toujours non résolue — `titiler`/`duckdb-api` restent
  accessibles uniquement depuis le réseau docker interne.
