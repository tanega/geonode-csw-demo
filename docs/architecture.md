# Architecture — geonode-demo

## Objectif

Projet d'apprentissage OGC CSW: découverte/recherche de métadonnées spatiales via GeoNode (pycsw), avec un stack de stockage hybride et une couche analytique/preview cloud-native.

## Stack

| Composant | Rôle |
|---|---|
| Traefik | Reverse proxy / routing, remplace Nginx |
| GeoNode | Portail + catalogue CSW (pycsw intégré) |
| PostgreSQL/PostGIS | Backend vecteur pour GeoServer |
| GeoServer | Sert WMS/WFS/WCS depuis PostGIS + rasters |
| MinIO | Object storage local (simule S3) pour GeoParquet/COG |
| DuckDB | Requêtage analytique direct sur GeoParquet |
| TiTiler | Tuiles dynamiques (XYZ) depuis COG |

## Grandes étapes

1. **Socle conteneurisé** — Compose de base: Traefik, PostGIS, GeoNode, GeoServer.
2. **Déploiement GeoNode + CSW** (vérifié — voir [step2-geonode-csw.md](step2-geonode-csw.md)) — `GetCapabilities`/`GetRecords` validés sur `/catalogue/csw`, 2 datasets test publiés (vecteur + raster). Limitation connue: Traefik ne route pas encore (socket Docker bloqué, probablement Enhanced Container Isolation de Docker Desktop).
3. **Storage cloud-natif secondaire** (vérifié — voir [step3-cloud-native-storage.md](step3-cloud-native-storage.md)) — MinIO démarré + bucket créé, scripts conversion (`gdal_translate` → COG, `ogr2ogr`/`gpq` → GeoParquet), 1 raster + 1 vecteur convertis et uploadés.
4. **Couche analytics/preview** (vérifié — voir [step4-analytics-preview.md](step4-analytics-preview.md)) — DuckDB (extension spatial, wrapper FastAPI dans `analytics/`) sur GeoParquet, TiTiler sur COG, tous deux lisant depuis MinIO.
5. **Jeux de données test** (vérifié — voir [step5-dual-ingestion.md](step5-dual-ingestion.md)) — 1 dataset vecteur + 1 raster, ingérés en double (GeoServer via `importlayers` à l'étape 2 + version cloud-native COG/GeoParquet dans MinIO à l'étape 3).
6. **Pont catalogage** (vérifié — voir [step6-catalog-bridge.md](step6-catalog-bridge.md)) — CSW référence aussi les assets cloud-natifs, via des `Link` GeoNode (lien externe dans metadata); STAC écarté pour ce projet d'apprentissage (voir doc pour la justification).
7. **Exposition endpoints + CORS** — lister tous les endpoints consommables, config CORS pour le futur frontend externe.
8. **Validation bout-en-bout** — CSW GetRecords → WFS GetFeature / preview COG-GeoParquet, avant de démarrer le frontend.
9. **Frontend standalone** — étape séparée: structure de l'app, choix des librairies/packages.

## Décisions actées

- Stack hybride confirmé malgré la complexité de deux stacks à gérer (GeoServer + cloud-natif) — priorité à l'apprentissage des deux approches.
- Traefik plutôt que Nginx pour le reverse proxy.
- Frontend: app standalone externe consommant les endpoints OGC de GeoNode — structure/libs à définir plus tard.
