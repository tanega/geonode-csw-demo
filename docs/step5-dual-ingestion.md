# Étape 5 — Jeux de données test ingérés en double

**Statut: vérifié le 2026-07-30.** Cette étape n'ajoute rien de nouveau —
elle constate que les étapes 2 et 3 combinées satisfont déjà le critère
"1 dataset vecteur + 1 raster, ingérés en double (GeoServer + version
cloud-native)" de `architecture.md`, et documente la vérification croisée.

## Les deux copies, par dataset

| Dataset | Copie GeoServer (étape 2) | Copie cloud-native (étape 3) |
|---|---|---|
| Raster (`lisbon_elevation`) | Importé via `importlayers` → servi en WMS/WCS par GeoServer | `cog/lisbon_elevation_cog.tif` dans MinIO (COG) |
| Vecteur (`ne_110m_admin_0_countries`) | Importé via `importlayers` → servi en WMS/WFS par GeoServer | `geoparquet/ne_110m_admin_0_countries.parquet` dans MinIO (GeoParquet) |

## Vérification croisée

Copie GeoServer — confirmée via CSW (2 records, cf. étape 2):

```bash
docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&elementSetName=full&resultType=results" \
  | grep -o "<dc:title>[^<]*</dc:title>"
# <dc:title>lisbon_elevation</dc:title>
# <dc:title>ne_110m_admin_0_countries</dc:title>
```

Copie cloud-native — confirmée dans MinIO (cf. étape 3/4):

```bash
docker run --rm --network geonode-demo_geonode-net minio/mc:latest -c '
mc alias set localminio http://minio:9000 minioadmin <MINIO_ROOT_PASSWORD> >/dev/null &&
mc ls --recursive localminio/geonode-demo
'
# cog/lisbon_elevation_cog.tif
# geoparquet/ne_110m_admin_0_countries.parquet
```

## Critère de sortie de l'étape

- [x] Raster présent dans les deux stacks (GeoServer + COG/MinIO)
- [x] Vecteur présent dans les deux stacks (GeoServer + GeoParquet/MinIO)

## Suite

Étape 6: faire en sorte que le catalogue CSW référence aussi explicitement
la copie cloud-native de chaque dataset (pas seulement la copie GeoServer).
