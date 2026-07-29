# Étape 2 — GeoNode + CSW

## Avant le premier démarrage

Les tags d'image et variables d'env du `docker-compose.yml` sont calqués sur la
stack officielle GeoNode. À revalider contre la doc/release notes de la version
GeoNode ciblée avant de lancer:

- https://github.com/GeoNode/geonode/blob/master/docker-compose.yml
- https://docs.geonode.org/ (section installation Docker)

## Démarrage

```bash
cp .env.example .env   # renseigner les secrets
docker compose up -d db redis
docker compose up -d django celery geoserver traefik
docker compose logs -f django
```

Ajouter `127.0.0.1 geonode.localhost` dans `/etc/hosts` (ou la valeur de `DOMAIN`).

## Vérification CSW

Une fois `django` healthy:

```bash
# GetCapabilities
curl "http://geonode.localhost/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities"

# GetRecords
curl "http://geonode.localhost/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&resultType=results"
```

Réponses attendues: XML `csw:Capabilities` puis `csw:GetRecordsResponse` (vide
tant qu'aucun jeu de données n'est publié dans GeoNode).

## Critère de sortie de l'étape

- [ ] `GetCapabilities` répond 200 avec un XML valide
- [ ] `GetRecords` répond 200 (même liste vide)
- [ ] Au moins un dataset publié dans GeoNode apparaît dans `GetRecords`
