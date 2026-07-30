# Étape 6 — Pont catalogage (CSW ↔ assets cloud-natifs)

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

Objectif (`architecture.md`): faire en sorte que le catalogue CSW référence
aussi les assets cloud-natifs (COG/GeoParquet dans MinIO, étapes 3/4), pas
seulement les couches GeoServer.

## Décision: liens externes dans les metadata, pas de STAC

`architecture.md` proposait deux options — lien externe dans les metadata,
ou catalogue STAC complémentaire. Choix: **liens externes**, via le modèle
`Link` de GeoNode (mécanisme déjà natif, aucune dépendance supplémentaire).
Un catalogue STAC séparé aurait dupliqué un mécanisme de découverte que ce
projet a justement pour but d'apprendre côté CSW/pycsw, pour un bénéfice
marginal ici (2 datasets de test) — écarté, à reconsidérer si le nombre
d'assets cloud-natifs grandit significativement.

## Mécanisme: `ResourceBase.download_links()`

`geonode/base/models.py` — `download_links()` construit la liste des
`dct:references` **à la demande, à chaque requête `GetRecords`**, en lisant
`self.link_set.all()` (pas de cache, pas de régénération XML nécessaire):

```python
def download_links(self):
    for link in self.link_set.all():
        if link.link_type == "html":
            links.append((self.title, "Web address (URL)", "WWW:LINK-1.0-http--link", link.url))
        elif link.link_type in ("OGC:WMS", "OGC:WFS", "OGC:WCS"):
            ...
        else:  # "data", "image", "original"
            description = f"{self.title} ({link.name} Format)"
            links.append((self.title, description, "WWW:DOWNLOAD-1.0-http--download", link.url))
```

Conséquence pratique: ajouter des `Link` en base suffit — pas besoin de
`dataset.save()` ni de retrigger le signal `catalogue_post_save`.

Script: `data/scripts/link_cloud_native_assets.py`, idempotent
(`get_or_create` sur `resource`+`url`), ajoute pour chaque dataset:

| Dataset | Link `data` (téléchargement brut) | Link `html` (accès applicatif) |
|---|---|---|
| `lisbon_elevation` | COG sur MinIO | Preview TiTiler (rendu dynamique depuis le COG) |
| `ne_110m_admin_0_countries` | GeoParquet sur MinIO | `duckdb-api` `/countries` (requêtes spatiales) |

```bash
docker cp data/scripts/link_cloud_native_assets.py \
  geonode-demo-django-1:/tmp/link_cloud_native_assets.py
docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py shell < /tmp/link_cloud_native_assets.py"
```

## ⚠️ Piège: une virgule dans `Link.name` corrompt le XML CSW

Pour les links de type `data`/`image`/`original`, `download_links()`
interpole `link.name` dans une description, puis pycsw sérialise chaque
lien en **CSV maison** (`name,description,protocol,url` joints par `,`,
plusieurs liens joints par `^` — voir
`pycsw.core.util.jsonify_links`, branche `except json.decoder.JSONDecodeError`
qui fait `link.split(',')` sans échappement).

Première tentative: `name="Cloud-Optimized GeoTIFF (COG, MinIO)"` (avec
virgule) → XML produit corrompu, champs décalés:
```xml
<dct:references scheme=" MinIO) Format)">WWW:DOWNLOAD-1.0-http--download</dct:references>
```
(le `scheme` XML contient un fragment du nom, et le texte de l'élément est
le protocole — `url` a disparu du tout). Corrigé en retirant la virgule:
`"Cloud-Optimized GeoTIFF (COG) on MinIO"`. Les liens de type `html` ne sont
pas concernés (leur description est le literal fixe `"Web address (URL)"`,
`link.name` n'y entre pas).

**Règle à retenir:** ne jamais mettre de virgule dans le `name` d'un `Link`
GeoNode de type `data`/`image`/`original`.

## Pré-requis: Traefik doit router (branche `infra-traefik-api-version-fix`)

Les liens `html` (`WWW:LINK-1.0-http--link`) pointent vers
`http://geonode.localhost/titiler/...` et `/analytics/...` — donc vers
Traefik, pas directement vers les conteneurs. Ce pont ne fonctionne
end-to-end que depuis la correction Traefik (pin `v3.7.9`, cf.
`CLAUDE.md` "Traefik was broken — fixed by pinning a newer image tag").
Deux ajouts complémentaires faits dans cette étape (pas dans la correction
Traefik elle-même, qui ne les incluait pas):

- `titiler`/`duckdb-api` recevaient déjà `PathPrefix` mais pas de
  `stripprefix` — Traefik forwardait `/titiler/cog/info` tel quel, or
  `titiler` route `/cog/info` (sans le préfixe) → 404. Ajout de
  `traefik.http.middlewares.<service>-strip.stripprefix.prefixes=/<prefix>`
  + `traefik.http.routers.<service>.middlewares=<service>-strip` pour
  `titiler` et `duckdb-api`.
- Le bucket MinIO était privé par défaut → le lien `data` (téléchargement
  direct du COG/GeoParquet) répondait 403. `mc anonymous set download
  localminio/geonode-demo` (lecture seule, pas d'écriture) pour que le lien
  de catalogue soit réellement téléchargeable, pas juste une URL de façade.

## Vérification

Les 4 références apparaissent dans `GetRecords` et répondent 200:

```bash
docker exec geonode-demo-django-1 curl -s -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&elementSetName=full&resultType=results" \
  | grep -o '<dct:references[^/]*>[^<]*</dct:references>' | grep -iE "minio|titiler|analytics"
```
```
<dct:references scheme="WWW:LINK-1.0-http--link">http://geonode.localhost/titiler/cog/preview.png?url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif</dct:references>
<dct:references scheme="WWW:DOWNLOAD-1.0-http--download">http://minio.geonode.localhost/geonode-demo/cog/lisbon_elevation_cog.tif</dct:references>
<dct:references scheme="WWW:DOWNLOAD-1.0-http--download">http://minio.geonode.localhost/geonode-demo/geoparquet/ne_110m_admin_0_countries.parquet</dct:references>
<dct:references scheme="WWW:LINK-1.0-http--link">http://geonode.localhost/analytics/countries</dct:references>
```

Chaque URL testée directement via Traefik (port 80, `Host` header):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: geonode.localhost" \
  "http://localhost/titiler/cog/preview.png?url=s3%3A%2F%2Fgeonode-demo%2Fcog%2Flisbon_elevation_cog.tif"   # 200
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: minio.geonode.localhost" \
  "http://localhost/geonode-demo/cog/lisbon_elevation_cog.tif"                                              # 200
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: minio.geonode.localhost" \
  "http://localhost/geonode-demo/geoparquet/ne_110m_admin_0_countries.parquet"                              # 200
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: geonode.localhost" \
  "http://localhost/analytics/countries"                                                                    # 200
```

## Critère de sortie de l'étape

- [x] Le COG raster (étape 3) est référencé dans le CSW record de
      `lisbon_elevation` (lien de téléchargement + lien de preview)
- [x] Le GeoParquet vecteur (étape 3) est référencé dans le CSW record de
      `ne_110m_admin_0_countries` (lien de téléchargement + lien analytics)
- [x] Toutes les URL référencées répondent 200 en conditions réelles
      (via Traefik, port 80)

## Limites connues / reste à faire

- Les liens sont ajoutés manuellement via script one-shot, pas
  automatiquement à l'import (`importlayers` ne connaît pas MinIO) — si de
  nouveaux datasets sont ajoutés, il faut étendre
  `link_cloud_native_assets.py` ou l'exécuter avec de nouveaux paramètres.
- pycsw expose ces liens uniquement via l'ancien format `dct:references`
  (profil `csw:Record`/Dublin Core); le mapping vers le profil ISO complet
  (`gmd:MD_Metadata`, cf. `full_metadata.xml`) n'a pas été vérifié pour ces
  nouveaux liens, seul le format DC utilisé dans `GetRecords` par défaut.
- Étape 7 (endpoints + CORS) et étape 8 (validation bout-en-bout) restent à
  faire.
