# Étape 3 — Storage cloud-natif secondaire (MinIO + conversions)

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

## Ce qui existe déjà vs. ce que cette étape a ajouté

Le service `minio` et les volumes associés étaient déjà scaffoldés dans
`docker-compose.yml`/`.env.example` depuis l'étape 1/2 (jamais démarré ni
testé). Cette étape:

- démarre effectivement `minio` (`docker compose up -d minio`) et crée le
  bucket applicatif (`geonode-demo`, valeur de `MINIO_BUCKET`) ;
- ajoute les 3 scripts annoncés dans `data/scripts/README.md`
  (`to_cog.sh`, `to_geoparquet.sh`, `upload_minio.sh`), testés sur les
  jeux de données de l'étape 2 ;
- valide qu'un raster et un vecteur convertis atterrissent bien dans le
  bucket.

## ⚠️ MinIO n'est pas exposé sur le host

`docker-compose.yml` ne publie aucun port pour `minio` (ni API `9000`, ni
console `9001`) — seul un label Traefik existe, inutile tant que Traefik ne
route rien (limitation connue depuis l'étape 2). Conséquence: `mc` doit
tourner **dans le réseau docker**, pas sur le host. `upload_minio.sh`
contourne ça en lançant un conteneur `minio/mc` jetable attaché à
`geonode-demo_geonode-net`, avec le fichier local monté en bind-mount
read-only.

## Scripts (`data/scripts/`)

```bash
# Raster → COG (gdal_translate, driver COG natif = pas besoin de gdaladdo séparé)
data/scripts/to_cog.sh data/raw/lisbon_elevation.tif data/processed/lisbon_elevation_cog.tif

# Vecteur → GeoParquet (ogr2ogr driver Parquet)
data/scripts/to_geoparquet.sh data/raw/ne_110m_admin_0_countries.geojson \
  data/processed/ne_110m_admin_0_countries.parquet

# Upload vers MinIO (démarre un conteneur mc jetable sur geonode-net)
data/scripts/upload_minio.sh data/processed/lisbon_elevation_cog.tif cog/lisbon_elevation_cog.tif
data/scripts/upload_minio.sh data/processed/ne_110m_admin_0_countries.parquet \
  geoparquet/ne_110m_admin_0_countries.parquet
```

`upload_minio.sh` lit `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`/`MINIO_BUCKET`
depuis `.env` par `grep` ciblé plutôt que `source .env` — `.env` contient des
valeurs multi-mots non quotées (ex. `GEOSERVER_JAVA_OPTS`) qu'un `source`
brut ne peut pas parser sans erreur.

`data/processed/` est le répertoire de sortie des conversions locales, non
versionné (à ajouter dans `.gitignore` au même titre que `data/raw/*` si des
fichiers volumineux y transitent — actuellement vide dans git, contenu
généré à la demande).

## Vérification

```bash
docker run --rm --entrypoint sh --network geonode-demo_geonode-net minio/mc:latest -c '
mc alias set localminio http://minio:9000 minioadmin <MINIO_ROOT_PASSWORD> >/dev/null &&
mc ls --recursive localminio/geonode-demo
'
```

Résultat observé:

```
[...] 515KiB STANDARD cog/lisbon_elevation_cog.tif
[...] 361KiB STANDARD geoparquet/ne_110m_admin_0_countries.parquet
```

COG vérifié via `gdalinfo` (`LAYOUT=COG`, overviews générées). GeoParquet
vérifié via `gpq describe` (177 lignes, `GeoParquet Version 1.1.0`).

## Critère de sortie de l'étape

- [x] `minio` démarre et reste `Up`
- [x] Bucket applicatif créé
- [x] 1 raster converti en COG et uploadé
- [x] 1 vecteur converti en GeoParquet et uploadé

## Reste à faire avant l'étape 4

- Étape 4 (DuckDB + TiTiler) consommera ces mêmes objets MinIO — pas encore
  branché.
- Pont catalogage CSW ↔ assets cloud-natifs (étape 6) toujours ouvert : ces
  objets MinIO ne sont pas référencés dans le catalogue pycsw.
- Limitation Traefik toujours non résolue (cf étape 2) — MinIO reste
  inaccessible en dehors du réseau docker interne tant que ce n'est pas
  réglé.
