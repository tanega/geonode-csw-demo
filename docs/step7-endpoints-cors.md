# Étape 7 — Exposition endpoints + CORS

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

Objectif (`architecture.md`): lister tous les endpoints consommables par le
futur frontend externe, et s'assurer que chacun répond avec les en-têtes
CORS nécessaires (le frontend tournera sur une origine différente —
`http://localhost:xxxx` en dev — de celle de la stack, `geonode.localhost`).

## Catalogue des endpoints

Tous les exemples ci-dessous passent par Traefik (port 80, header `Host`),
le chemin réellement utilisable par un frontend externe.

| Service | Endpoint | Exemple |
|---|---|---|
| CSW (pycsw, dans django) | `GetCapabilities` / `GetRecords` | `http://geonode.localhost/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&elementSetName=full&resultType=results` |
| GeoServer WMS | `GetMap` / `GetCapabilities` / `GetLegendGraphic` | `http://geonode.localhost/geoserver/ows?service=WMS&request=GetMap&layers=geonode:ne_110m_admin_0_countries&format=image/png&...` |
| GeoServer WFS | `GetFeature` (vecteur) | `http://geonode.localhost/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typename=geonode:ne_110m_admin_0_countries&outputFormat=json` |
| GeoServer WCS | `GetCoverage` (raster) | `http://geonode.localhost/geoserver/ows?service=WCS&request=GetCoverage&coverageid=geonode__lisbon_elevation&format=image/tiff&version=2.0.1` |
| TiTiler | `preview.png` / `info` / tuiles XYZ sur COG | `http://geonode.localhost/titiler/cog/preview.png?url=s3://geonode-demo/cog/lisbon_elevation_cog.tif` |
| DuckDB analytics (`analytics/app.py`) | `/countries`, `/countries/{adm0_a3}` (JSON sur GeoParquet) | `http://geonode.localhost/analytics/countries?limit=10` |
| MinIO | téléchargement direct objet (COG/GeoParquet) | `http://minio.geonode.localhost/geonode-demo/geoparquet/ne_110m_admin_0_countries.parquet` |

Les URL exactes par dataset (WMS/WFS/WCS, MinIO, TiTiler, analytics) sont
générées dynamiquement par `download_links()` et visibles dans chaque record
`GetRecords` (`dct:references`) — voir [step6-catalog-bridge.md](step6-catalog-bridge.md).
C'est la liste de référence: le frontend est censé les découvrir via CSW,
pas les coder en dur.

## CORS: état par service avant cette étape

Testé avec un header `Origin: http://localhost:5173` (port dev Vite
arbitraire, simule le futur frontend) sur chaque famille d'endpoint:

| Service | CORS avant | Cause |
|---|---|---|
| TiTiler | ✅ déjà actif | `titiler.application.settings.ApiSettings.cors_origins` vaut `"*"` par défaut — `CORSMiddleware` déjà monté dans l'image officielle |
| MinIO | ✅ déjà actif | config serveur `api.cors_allow_origin=*` par défaut (RELEASE.2025-09-07), vérifié via `mc admin config get localminio api` |
| Django/CSW | ❌ absent | `django-cors-headers` est installé et son middleware monté (image GeoNode), mais `CORS_ALLOW_ALL_ORIGINS` (lu par `geonode/settings.py:897`) n'était pas positionné → défaut `False`, aucun header émis |
| GeoServer | ❌ absent | le filtre CORS de Tomcat (`org.apache.catalina.filters.CorsFilter`) existe dans `web.xml` mais est **commenté** dans l'image `geonode/geoserver` — pas configurable par variable d'env |
| DuckDB analytics (`analytics/app.py`) | ❌ absent | app FastAPI maison, aucun `CORSMiddleware` n'y avait été ajouté |

## Corrections apportées

Deux mécanismes différents selon ce que chaque service permet, pas un choix
arbitraire:

- **Django**: ajout de `CORS_ALLOW_ALL_ORIGINS: "True"` dans `x-geonode-env`
  (`docker-compose.yml`) — le mécanisme existe déjà côté image, il manquait
  juste la variable.
- **GeoServer**: pas d'équivalent env-configurable côté image (filtre
  commenté dans `web.xml`, patcher l'image serait plus invasif qu'un
  middleware Traefik). Ajout d'un middleware Traefik dédié
  (`traefik.http.middlewares.geoserver-cors.headers.*`) sur le router
  `geoserver`, même pattern que les labels `stripprefix` déjà utilisés pour
  `titiler`/`duckdb-api` (étape 6).
- **DuckDB analytics**: app FastAPI maison → `CORSMiddleware` ajouté
  directement dans `analytics/app.py`, même mécanisme que TiTiler
  (cohérent entre les deux apps FastAPI du projet, pas besoin de Traefik ici).
- **TiTiler / MinIO**: rien à faire, déjà ouverts par défaut.

Pas de risque de double en-tête `Access-Control-Allow-Origin`: chaque
service n'a qu'un seul mécanisme CORS actif (soit applicatif, soit Traefik,
jamais les deux en même temps sur le même router).

`*` (toutes origines) est un choix délibérément permissif, cohérent avec le
cadre du projet (apprentissage, frontend pas encore démarré, aucun de ces
endpoints ne nécessite de cookie de session — à restreindre à l'origine
réelle du frontend si ce projet dépassait ce cadre).

## Vérification

```bash
curl -s -D - -o /dev/null -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
  "http://localhost/geoserver/wms?service=WMS&version=1.3.0&request=GetCapabilities" | grep -i access-control
# Access-Control-Allow-Origin: *

curl -s -D - -o /dev/null -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
  "http://localhost/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities" | grep -i access-control
# Access-Control-Allow-Origin: *

curl -s -D - -o /dev/null -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
  "http://localhost/analytics/countries?limit=1" | grep -i access-control
# Access-Control-Allow-Origin: *

curl -s -D - -o /dev/null -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" \
  "http://localhost/titiler/cog/info?url=s3://geonode-demo/cog/lisbon_elevation_cog.tif" | grep -i access-control
# Access-Control-Allow-Origin: http://localhost:5173  (echo de l'origin, comportement standard starlette CORSMiddleware)

curl -s -D - -o /dev/null -H "Host: minio.geonode.localhost" -H "Origin: http://localhost:5173" \
  "http://localhost/geonode-demo/cog/lisbon_elevation_cog.tif" | grep -i access-control
# Access-Control-Allow-Origin: http://localhost:5173
```

## Critère de sortie de l'étape

- [x] Tous les endpoints consommables par le futur frontend sont listés
- [x] Les 5 familles de service répondent avec `Access-Control-Allow-Origin`
      pour une origine cross-site arbitraire
- [x] Aucune régression: chaque service garde un seul mécanisme CORS actif

## Limites connues / reste à faire

- `*` est correct pour ce projet d'apprentissage mais devrait être restreint
  à l'origine réelle du frontend en cas de mise en prod.
- Le filtre CORS de GeoServer reste commenté dans l'image — la solution
  Traefik fonctionne mais dépend de Traefik comme unique point d'entrée
  (cohérent avec la décision actée en étape 1, mais à refaire si GeoServer
  était un jour exposé sans Traefik devant).
