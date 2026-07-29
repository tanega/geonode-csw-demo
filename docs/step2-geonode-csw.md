# Étape 2 — GeoNode + CSW

**Statut: vérifié de bout en bout le 2026-07-29** (stack locale, `docker compose`).
Les 3 critères de sortie sont validés — détails et limitations connues ci-dessous.

## Corrections apportées à la stack officielle

Le `docker-compose.yml`/`.env.example` initiaux étaient calqués sur la stack
GeoNode officielle mais contenaient plusieurs erreurs, corrigées en testant
réellement le démarrage:

- `geonode/geonode:latest-ubuntu-26.04` n'existe pas sur Docker Hub → remplacé
  par `geonode/geonode:5.0.0` (vérifié via l'API Docker Hub).
- `django`/`celery` tournaient sans `entrypoint`/`command` → conteneur
  exécutait juste `/bin/bash` et sortait aussitôt. Ajout de
  `entrypoint: ["/usr/src/geonode/entrypoint.sh"]` +
  `command: "uwsgi --ini /usr/src/geonode/uwsgi.ini"` (django) /
  `"celery-cmd"` (celery).
- GeoNode utilise **deux rôles/DB Postgres distincts** (`geonode` pour l'app,
  `geonode_data` pour le datastore GeoServer) — l'image `geonode/postgis` les
  crée nativement à partir des variables `GEONODE_DATABASE*`/
  `GEONODE_GEODATABASE*` (pas besoin de script d'init custom).
- `geoserver` crashait (JVM: `Could not find or load main class
  XX:ParallelGCThreads=4`) car `GEOSERVER_JAVA_OPTS` n'était pas défini →
  ajouté (valeurs réduites: `-Xms512m -Xmx1G`, cf `.env.example`).
- `django` plantait silencieusement sur `invoke prepare`
  (`KeyError: 'OAUTH2_CLIENT_ID'`, visible seulement via
  `docker cp django:/usr/src/geonode/invoke.log`, pas dans `docker logs`) →
  ajout de `OAUTH2_CLIENT_ID`/`OAUTH2_CLIENT_SECRET`.

## ⚠️ Limitation connue: Traefik ne route rien

Traefik ne parvient pas à lire le socket Docker monté
(`/var/run/docker.sock`) — erreur `Error response from daemon: ` (vide) en
boucle, aucun router découvert. Symptôme classique de la fonctionnalité
**Enhanced Container Isolation** de Docker Desktop (bloque l'accès au socket
Docker depuis les conteneurs par sécurité). À vérifier/désactiver dans
Docker Desktop → Settings → General, ou passer par un
`docker-socket-proxy` dédié. Pas corrigeable depuis le `docker-compose.yml`
seul.

En attendant, la vérification ci-dessous contourne Traefik en tapant
directement sur `django` via le réseau interne (`docker exec` +
`Host: django`, ou `http://django:8000` depuis un autre conteneur du réseau).

## Jeux de données de test

| Type | Fichier | Source |
|---|---|---|
| Raster | `data/raw/lisbon_elevation.tif` (~905 KB, GeoTIFF WGS84, 547×421px, MNT) | [GeoTIFF/test-data](https://github.com/GeoTIFF/test-data) — `files/LisbonElevation.tif` |
| Vecteur | `data/raw/ne_110m_admin_0_countries.geojson` (~819 KB, polygones pays) | [Natural Earth](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson) — domaine public |

Ni versionnés (`.gitignore` exclut `data/raw/*`) ni importés automatiquement.
Import réel testé via la commande GeoNode `importlayers` (voir plus bas).

**Note vecteur:** le GeoJSON brut est refusé par l'importer GeoNode ("No
handlers found for this dataset type/action"). Converti en GeoPackage avec
géométries forcées en MULTIPOLYGON (Natural Earth mélange POLYGON/MULTIPOLYGON,
que GeoNode refuse aussi tel quel):
```bash
ogr2ogr -f GPKG -nlt MULTIPOLYGON -nlt PROMOTE_TO_MULTI \
  ne_countries_multi.gpkg ne_110m_admin_0_countries.geojson
```

## Démarrage

```bash
cp .env.example .env   # renseigner les secrets
docker compose up -d db redis                       # attendre ~10s (init DB)
docker compose up -d django celery geoserver traefik
docker compose logs -f django                        # ~2-3 min: migrations, prepare, fixtures, uwsgi
```

## Vérification CSW (contournement Traefik)

```bash
# GetCapabilities
docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities"

# GetRecords (elementSetName est obligatoire)
docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&elementSetName=full&resultType=results"
```

## Import des jeux de test

```bash
docker cp lisbon_elevation.tif geonode-demo-django-1:/data/
docker cp ne_countries_multi.gpkg geonode-demo-django-1:/data/

docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py importlayers /data/lisbon_elevation.tif \
   -u admin -p <GEONODE_ADMIN_PASSWORD> -hh http://django:8000"

docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py importlayers /data/ne_countries_multi.gpkg \
   -u admin -p <GEONODE_ADMIN_PASSWORD> -hh http://django:8000"
```

`-hh http://django:8000` cible django lui-même via le réseau docker interne
(contournement Traefik nécessaire tant que la limitation ci-dessus n'est pas
résolue).

## Critère de sortie de l'étape

- [x] `GetCapabilities` répond 200 avec un XML valide (`pycsw 3.0.0b1`)
- [x] `GetRecords` répond 200 (testé vide, puis avec résultats)
- [x] Au moins un dataset publié apparaît dans `GetRecords` — 2/2 testés
      (`lisbon_elevation` raster, `ne_110m_admin_0_countries` vecteur),
      metadata complètes (WMS/WFS/WCS, bbox, thumbnail)

## Reste à faire avant de considérer l'étape totalement close

- Résoudre l'accès Traefik → socket Docker (Docker Desktop settings)
- Fichier `infra/postgres/init-geonode-db.sh` devenu inutile (l'image
  `geonode/postgis` gère nativement la création des DB) — à supprimer
  manuellement, la suppression a été bloquée par les permissions du
  sandbox agent.
