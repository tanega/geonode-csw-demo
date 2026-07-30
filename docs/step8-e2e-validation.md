# Étape 8 — Validation bout-en-bout

**Statut: vérifié le 2026-07-30** (stack locale, `docker compose`).

Objectif (`architecture.md`): rejouer, avant de démarrer le frontend, le
chemin exact qu'il suivra — CSW `GetRecords` comme point d'entrée unique,
puis résolution des liens vers WFS/WMS (vecteur) et TiTiler/GeoParquet
(raster/analytics) — le tout via Traefik avec un `Origin` cross-site pour
vérifier que CORS (étape 7) fonctionne réellement sur ce chemin, pas
seulement en isolation par service.

## Chaîne vecteur: CSW → WFS `GetFeature`

1. `GetRecords` renvoie le dataset `ne_110m_admin_0_countries` avec, entre
   autres `dct:references`, une URL WFS déjà prête à l'emploi:
   ```
   http://geonode.localhost/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typename=geonode:ne_110m_admin_0_countries&outputFormat=json&srs=EPSG:4326&srsName=EPSG:4326
   ```
2. Le frontend suit ce lien tel quel (aucune connaissance préalable du
   layer name requise — il vient du catalogue):
   ```bash
   curl -s -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
     "http://localhost/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typename=geonode:ne_110m_admin_0_countries&outputFormat=json&maxFeatures=1"
   ```
   → `200`, `Access-Control-Allow-Origin: *`, GeoJSON `FeatureCollection`
   avec géométrie `MultiPolygon`.

### ⚠️ Piège: noms d'attributs différents entre WFS et le GeoParquet cloud-natif

Le WFS de GeoServer renvoie les attributs en **minuscules**
(`admin`, `adm0_a3`, `continent`) — normalisation standard de GeoServer sur
les noms de colonnes PostGIS. Le service `analytics` (DuckDB sur le
GeoParquet, étape 4) lit directement les colonnes du fichier source, qui
sont en **majuscules** (`ADMIN`, `ADM0_A3`, `CONTINENT` — cf.
`analytics/app.py`). Un frontend qui affiche les deux sources (couche
GeoServer + résultat analytics) pour le même dataset doit normaliser la
casse des clés lui-même — CSW/pycsw ne l'indique pas, ce n'est visible
qu'en comparant les réponses réelles.

## Chaîne raster: CSW → TiTiler preview

1. `GetRecords` renvoie le dataset `lisbon_elevation` avec un lien `html`
   pointant directement vers un preview TiTiler pré-construit:
   ```
   http://geonode.localhost/titiler/cog/preview.png?url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif
   ```
2. Suivi tel quel:
   ```bash
   curl -s -D - -o preview.png -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
     "http://localhost/titiler/cog/preview.png?url=s3://geonode-demo/cog/lisbon_elevation_cog.tif"
   ```
   → `200`, `Content-Type: image/png`, `Access-Control-Allow-Origin: http://localhost:5173`,
   PNG 547×421 valide (vérifié avec `file`).

## Chaîne analytics: CSW → DuckDB

1. `GetRecords` renvoie, pour `ne_110m_admin_0_countries`, un lien `html`
   vers l'API analytics: `http://geonode.localhost/analytics/countries`.
2. Suivi tel quel:
   ```bash
   curl -s -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
     "http://localhost/analytics/countries?limit=3"
   ```
   → `200`, `Access-Control-Allow-Origin: *`, JSON trié par surface
   décroissante (Antarctica, Russia, Canada pour `limit=3`).

## Résultat

Les trois chaînes fonctionnent de bout en bout, via Traefik, avec un
`Origin` cross-site — exactement les conditions dans lesquelles le futur
frontend externe opérera. Aucun accès direct à un conteneur nécessaire (pas
de `docker exec`): tout passe par `http://geonode.localhost` /
`http://minio.geonode.localhost` sur le port 80, la même surface
qu'un navigateur verrait.

## Critère de sortie de l'étape

- [x] CSW `GetRecords` → WFS `GetFeature` (vecteur) validé de bout en bout
- [x] CSW `GetRecords` → TiTiler preview (raster/COG) validé de bout en bout
- [x] CSW `GetRecords` → analytics DuckDB (GeoParquet) validé de bout en bout
- [x] Chaque chaîne testée avec un `Origin` cross-site (CORS réellement
      exercé, pas juste configuré)

## Limites connues / reste à faire

- Validation faite en ligne de commande (`curl`), pas depuis un vrai
  navigateur — un test navigateur réel (fetch cross-origin) reste à faire
  une fois le frontend démarré (étape 9), pour couvrir le preflight
  `OPTIONS` que `curl` ne déclenche pas automatiquement sur GET simples.
- La divergence de casse WFS/GeoParquet (ci-dessus) n'est pas corrigée ici
  — à gérer côté frontend (étape 9) ou par une normalisation dans
  `analytics/app.py` si elle s'avère gênante.
