# IAM — Option A, signup path 2 (custom JSON endpoint)

**Statut: vérifié de bout en bout le 2026-07-30** (stack locale, `docker compose`).

Contexte: brainstorm IAM (admin = accès direct GeoServer/GeoNode UI;
editor/reader = frontend uniquement, upload vs lecture seule). Décision:
**Option A** — GeoNode reste l'autorité d'identité unique, pas de nouveau
composant (Authentik/Hanko écartés). GeoServer fait déjà confiance à GeoNode
en OAuth2 (`gs-sec-oauth2-geonode` bundlé + filtre `geonode-oauth2` déjà
configuré dans `geoserver_data/data/security/filter/`), et GeoNode fait déjà
tourner `django-oauth-toolkit` comme provider OAuth2 — vérifié en conteneur,
aucune config à ajouter côté GeoServer pour ça.

Pour le signup, 3 chemins possibles ont été discutés (redirection vers la
page GeoNode, endpoint JSON custom, POST HTML simulé côté frontend).
Choix: **chemin 2** — endpoint DRF custom dans GeoNode, pour que le futur
frontend poste du JSON directement, sans jamais afficher l'UI GeoNode.

## Ce qui a été vérifié avant d'écrire du code

- `ACCOUNT_EMAIL_VERIFICATION = "none"` — pas de confirmation email requise,
  un utilisateur créé est actif immédiatement.
- L'attribution des groupes au signup est **pilotée par signal**, pas par le
  formulaire: `geonode/people/signals.py::profile_post_save` est un
  receiver `post_save` sur le modèle User lui-même. Peu importe comment
  l'utilisateur est créé (formulaire allauth ou `create_user()` direct), le
  signal se déclenche et ajoute `anonymous` + `registered-members` (et
  `contributors` si `AUTO_ASSIGN_REGISTERED_MEMBERS_TO_CONTRIBUTORS` est
  vrai). Conséquence: pas besoin de réutiliser le `SignupForm` d'allauth
  (qui embarque un champ captcha) — un simple `create_user()` suffit à
  obtenir la même attribution de groupes que le flux HTML.
- Les groupes existants correspondent déjà 1:1 aux rôles cibles:
  `registered-members` = reader, `contributors` = editor (droits upload),
  `anonymous` = public. Aucun nouveau groupe à créer.
- `AUTO_ASSIGN_REGISTERED_MEMBERS_TO_CONTRIBUTORS` valait `True` par défaut
  (tout signup devenait editor) — mis à `"False"` pour que les nouveaux
  comptes soient reader par défaut; un admin promeut ensuite vers
  `contributors` via `/people/` (déjà vérifié fonctionnel) ou `/admin/`.
- Mécanisme d'injection sûr: `DJANGO_SETTINGS_MODULE` est lu dynamiquement
  partout où c'est utilisé (`manage.py`, et `tasks.py::_localsettings()` qui
  fait `os.getenv("DJANGO_SETTINGS_MODULE", "geonode.settings")` puis
  réinjecte cette même valeur dans le fichier override de `invoke prepare`
  — rien n'est codé en dur sur `geonode.settings`). Donc pointer
  `DJANGO_SETTINGS_MODULE` vers un module local qui fait
  `from geonode.settings import *` et ajoute une app + surcharge
  `ROOT_URLCONF` est sûr, sans reconstruire l'image — juste un volume +
  deux variables d'env.

## Implémentation

Nouveau répertoire `geonode-custom/`, monté en lecture seule dans `django`
et `celery` (pas buildé dans l'image):

```
geonode-custom/
  geonode_demo_settings.py   # from geonode.settings import *; + INSTALLED_APPS; ROOT_URLCONF
  geonode_demo_urls.py        # geonode.urls.urlpatterns + un nouveau path
  accounts_api/
    __init__.py
    apps.py
    serializers.py             # SignupSerializer
    views.py                   # SignupView (DRF APIView)
```

Noms de module distinctifs (`geonode_demo_settings`, pas `local_settings`)
pour éviter tout risque de collision une fois ajoutés au `PYTHONPATH`.

`docker-compose.yml` — dans `x-geonode-env` (partagé `django`+`celery`):
```yaml
DJANGO_SETTINGS_MODULE: geonode_demo_settings   # était: geonode.settings
PYTHONPATH: /opt/geonode-custom
AUTO_ASSIGN_REGISTERED_MEMBERS_TO_CONTRIBUTORS: "False"
```
Dans `x-geonode-volumes` (idem, partagé):
```yaml
- ./geonode-custom:/opt/geonode-custom:ro
```
Aucun label Traefik à ajouter — le nouveau path passe par le router
`django` existant (`Host(${DOMAIN})`), déjà CORS-ouvert (étape 7).

`SignupSerializer`: `username`, `email`, `password1`/`password2` (+
`first_name`/`last_name` optionnels), vérifie l'unicité username/email
(400 propre plutôt qu'une `IntegrityError` 500), valide la force du mot de
passe avec `django.contrib.auth.password_validation.validate_password`
(mêmes `AUTH_PASSWORD_VALIDATORS` que le formulaire HTML). `create()` fait
juste `User.objects.create_user(...)` — le signal `profile_post_save` fait
le reste (attribution des groupes).

## Vérification

```bash
# HTML signup existant — pas de régression après le changement de settings module
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: django" "http://localhost:8000/account/signup/"
# 200

# CSW — pas de régression non plus
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: django" \
  "http://localhost:8000/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities"
# 200

# Nouveau endpoint JSON
curl -s -X POST -H "Host: django" -H "Content-Type: application/json" \
  -d '{"username":"testreader","email":"testreader@example.com","password1":"Sup3r-Secret!9","password2":"Sup3r-Secret!9"}' \
  "http://localhost:8000/api/v2/signup/"
# 201 {"id":1001,"username":"testreader","email":"testreader@example.com"}

# Groupes attribués
python manage.py shell -c "
from django.contrib.auth import get_user_model
print(sorted(get_user_model().objects.get(username='testreader').groups.values_list('name', flat=True)))
"
# ['anonymous', 'registered-members']   -- PAS 'contributors'

# Doublon -> 400 propre
curl -s -w "\n%{http_code}\n" -X POST ... (même payload)
# {"success":false,"errors":["A user with that username already exists."],"code":"invalid"}
# 400

# Via Traefik, origine cross-site
curl -s -D - -X POST -H "Host: geonode.localhost" -H "Origin: http://localhost:5173" ...
# Access-Control-Allow-Origin: *
```

## Critère de sortie

- [x] `POST /api/v2/signup/` crée un utilisateur actif sans étape de
      confirmation email
- [x] Le nouvel utilisateur atterrit dans `registered-members` (reader) et
      pas dans `contributors` (editor) par défaut
- [x] Aucune régression sur le signup HTML existant ni sur CSW après le
      changement de `DJANGO_SETTINGS_MODULE`
- [x] Doublon username/email renvoie 400 propre (pas 500)
- [x] CORS déjà actif sur ce nouveau path (étape 7, aucune config
      supplémentaire nécessaire)

## Limites connues / reste à faire

- Pas de captcha ni de rate-limiting sur cet endpoint — le formulaire HTML
  d'allauth en embarque un (`CustomSignupView`), volontairement contourné
  ici en appelant `create_user()` directement. Acceptable pour ce projet
  d'apprentissage (frontend first-party, pas d'exposition publique large),
  à ajouter si ce projet dépassait ce cadre (ex: `django-ratelimit` sur la
  vue, ou un forward-auth/rate-limit au niveau Traefik).
- Le login (OAuth2 password grant, chemin 1 discuté précédemment) n'est
  pas encore implémenté — reste à créer l'`Application` OAuth2 dédiée
  (`authorization_grant_type=password`) dans `/admin/` et documenter le flux.
- Promotion editor (`contributors`) reste manuelle via `/people/`/`/admin/`
  — pas de self-service ni de workflow de demande côté frontend.
