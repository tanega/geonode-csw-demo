# IAM — Option A, login (OAuth2 password grant)

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

Suite de [iam-option-a-signup.md](iam-option-a-signup.md) — "chemin 1" du
brainstorm login: le frontend collecte username/password lui-même et poste
directement à `/o/token/` de GeoNode (`django-oauth-toolkit`, déjà provider
OAuth2/OIDC dans l'image), sans jamais rediriger vers une page GeoNode.

## Application OAuth2 dédiée

Une seule `Application` existait déjà: "GeoServer" (id 1001, `confidential`,
`authorization-code`) — c'est le pont GeoServer→GeoNode existant, à ne pas
toucher. Nouvelle Application créée pour le frontend:
`data/scripts/create_frontend_oauth_app.py` (idempotent, même convention
que `link_cloud_native_assets.py` de l'étape 6):

```bash
docker cp data/scripts/create_frontend_oauth_app.py \
  geonode-demo-django-1:/tmp/create_frontend_oauth_app.py
docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py shell < /tmp/create_frontend_oauth_app.py"
```

- `client_type=public` — l'app est appelée depuis un frontend dont on ne
  garantit pas de backend confidentiel pour garder un secret; pas de
  `client_secret` à transmettre au token endpoint.
- `authorization_grant_type=password` — ROPC, tradeoff déjà discuté et
  accepté (frontend first-party, pas de MFA/social-login prévu ici).

## Flux testé

```bash
curl -X POST http://geonode.localhost/o/token/ \
  -d "grant_type=password&username=<user>&password=<pwd>&client_id=<client_id>&scope=read%20write%20groups"
# {"access_token": "...", "expires_in": 36000, "token_type": "Bearer",
#  "scope": "read write groups", "refresh_token": "..."}
```

Rôle de l'utilisateur ensuite lu via l'endpoint OIDC userinfo (pas besoin de
décoder quoi que ce soit côté frontend — un GET suffit):

```bash
curl http://geonode.localhost/api/o/v4/userinfo/ -H "Authorization: Bearer <access_token>"
# {"sub": "1003", "email": "...", "preferred_username": "...",
#  "groups": ["registered-members", "anonymous"], ...}
```

`groups` contient directement `registered-members` (reader) ou
`contributors` (editor) selon le profil — c'est le claim à utiliser côté
frontend pour distinguer les deux rôles, pas besoin d'appel supplémentaire.

Mauvais mot de passe → `400 {"error": "invalid_grant", "error_description":
"Invalid credentials given."}`, propre.

## ⚠️ Piège: scope `openid` casse le refresh_token grant

GeoNode a l'OIDC activé (`OIDC_ENABLED=True`, clé RSA déjà configurée), et
`openid` fait partie des scopes proposés. Premier essai avec
`scope=openid read write groups`: le `/o/token/` initial répond bien (sans
`id_token` d'ailleurs — la RFC OIDC ne définit pas l'émission d'un id_token
pour le grant ROPC, `django-oauth-toolkit`/`oauthlib` ne le fait donc pas
ici, cohérent). Mais la requête `refresh_token` suivante plante en
**500** côté Django:

```
TypeError: combine() argument 1 must be datetime.date, not None
```
Traceback: `oauthlib/openid/connect/core/grant_types/refresh_token.py` →
`add_id_token()` → tente malgré tout de fabriquer un id_token rétroactif
au refresh dès que la portée `openid` est présente sur le token d'origine,
et plante en cherchant un timestamp d'authentification (`auth_time`) que le
grant password n'a jamais renseigné (pas de session interactive).

**Corrigé en ne demandant jamais le scope `openid` pour ce flux**:
`scope=read write groups`. Vérifié que `/api/o/v4/userinfo/` fonctionne
identiquement sans ce scope (200, claim `groups` présent) — `openid`
n'apportait donc aucun bénéfice ici (pas d'id_token de toute façon) tout en
cassant le refresh. Avec ce scope réduit, `refresh_token` répond `200` avec
une nouvelle paire access/refresh token.

**Règle à retenir:** ne jamais inclure `openid` dans les scopes demandés
pour le login ROPC de ce projet — uniquement pertinent si un jour un flux
`authorization_code` (redirection, pas ROPC) est ajouté pour un vrai besoin
d'`id_token`.

## Vérification

- [x] `POST /o/token/` (grant_type=password) renvoie access_token +
      refresh_token pour un utilisateur existant
- [x] Mauvais mot de passe → 400 `invalid_grant` propre
- [x] `/api/o/v4/userinfo/` renvoie le claim `groups` correct
      (`registered-members` par défaut, `contributors` si promu)
- [x] `refresh_token` fonctionne (une fois `openid` exclu du scope)
- [x] CORS déjà actif sur `/o/token/` via Traefik, origine cross-site
      testée (`Access-Control-Allow-Origin: *`)

## Limites connues / reste à faire

- ROPC reste discouraged par la spec OAuth2 pour des clients tiers — accepté
  ici uniquement parce que le frontend est first-party (même opérateur).
- Pas de rotation/révocation de refresh_token testée (`/o/revoke_token/`
  existe dans oauth-toolkit mais non exercé ici).
- Le claim `groups` ne distingue pas `is_staff`/`is_superuser` (admin) —
  si le frontend a besoin de savoir si l'utilisateur est admin, il faudra
  soit ajouter ce claim (custom OIDC claim mapping côté GeoNode), soit
  s'appuyer sur le fait qu'un admin n'utilisera de toute façon jamais ce
  flux (il se connecte directement à `/admin/`/GeoServer, pas via le
  frontend, cf. brainstorm IAM initial).
