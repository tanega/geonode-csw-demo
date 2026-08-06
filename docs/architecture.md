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
7. **Exposition endpoints + CORS** (vérifié — voir [step7-endpoints-cors.md](step7-endpoints-cors.md)) — catalogue de tous les endpoints consommables (CSW, WMS/WFS/WCS, TiTiler, analytics, MinIO); CORS activé sur les 3 services qui ne l'avaient pas par défaut (Django/CSW, GeoServer, analytics) — TiTiler et MinIO l'étaient déjà.
8. **Validation bout-en-bout** (vérifié — voir [step8-e2e-validation.md](step8-e2e-validation.md)) — CSW GetRecords → WFS GetFeature (vecteur), TiTiler preview (raster), et analytics DuckDB, rejoués via Traefik avec origine cross-site avant de démarrer le frontend.
9. **Frontend standalone** — étape séparée: structure de l'app, choix des librairies/packages. Auth (login/signup) + upload de dataset faits (Vue 3 + shadcn-vue + Pinia, `web/`). Catalogue de jeux de données + page détail faits (voir ci-dessous). Reste, dans l'ordre:
   1. ~~Catalogue de jeux de données (`GET /api/v2/resources`, liste/recherche)~~ — fait: page d'accueil (`HomeView.vue`) liste les ressources publiques, filtre client-side par titre. Recherche server-side pas disponible sur cette version de l'API GeoNode (`?search=`/`?title__icontains=` testés, ignorés silencieusement) — filtre client uniquement pour l'instant, acceptable vu le volume de données du projet.
   2. ~~Page détail dataset (métadonnées + liens WMS/WFS/WCS)~~ — fait: `DatasetDetailView.vue` (`/datasets/:pk`), liens groupés (OGC services / cloud-natif / téléchargements / métadonnées).
   3. Composant carte (lib à choisir — MapLibre GL JS pressenti) avec couches WMS GeoServer
   4. Aperçu raster cloud-natif (tuiles XYZ TiTiler en overlay carte)
   5. Aperçu analytics DuckDB sur un dataset vecteur cloud-natif
   6. Redirection upload → page détail de la ressource créée
   7. Tests composants (Vitest) + e2e (Playwright) au-delà du scaffold actuel — 2 specs e2e ajoutées pour catalogue/détail (`tests/e2e/dataset-catalogue.spec.ts`), Vitest composants toujours à faire

## Décisions actées

- Stack hybride confirmé malgré la complexité de deux stacks à gérer (GeoServer + cloud-natif) — priorité à l'apprentissage des deux approches.
- Traefik plutôt que Nginx pour le reverse proxy.
- Frontend: app standalone externe consommant les endpoints OGC de GeoNode — structure/libs à définir plus tard.
