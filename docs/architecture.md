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
2. **Déploiement GeoNode + CSW** — vérifier `GetCapabilities`/`GetRecords` sur l'endpoint `/catalogue/csw`.
3. **Storage cloud-natif secondaire** — MinIO + scripts conversion (`gdal_translate`/`gdaladdo` → COG, `ogr2ogr`/`gpq` → GeoParquet).
4. **Couche analytics/preview** — DuckDB (extension spatial) sur GeoParquet, TiTiler sur COG.
5. **Jeux de données test** — 1 dataset vecteur + 1 raster, ingérés en double (GeoServer + version cloud-native).
6. **Pont catalogage** — s'assurer que CSW référence aussi les assets cloud-natifs (lien externe dans metadata, ou catalogue STAC complémentaire à évaluer).
7. **Exposition endpoints + CORS** — lister tous les endpoints consommables, config CORS pour le futur frontend externe.
8. **Validation bout-en-bout** — CSW GetRecords → WFS GetFeature / preview COG-GeoParquet, avant de démarrer le frontend.
9. **Frontend standalone** — étape séparée: structure de l'app, choix des librairies/packages.

## Décisions actées

- Stack hybride confirmé malgré la complexité de deux stacks à gérer (GeoServer + cloud-natif) — priorité à l'apprentissage des deux approches.
- Traefik plutôt que Nginx pour le reverse proxy.
- Frontend: app standalone externe consommant les endpoints OGC de GeoNode — structure/libs à définir plus tard.
