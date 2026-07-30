"""
IAM option A, login (docs/iam-option-a-login.md): register a dedicated
django-oauth-toolkit Application for the future frontend, separate from the
existing "GeoServer" Application (id 1001, confidential,
authorization-code, used only for the GeoServer<->GeoNode auth bridge).

client_type="public": this app is meant to be called directly from a
frontend the user's browser talks to, with no guarantee of a confidential
backend to hold a secret. authorization_grant_type="password": lets the
frontend collect username/password itself and POST straight to /o/token/
(no redirect to a GeoNode-hosted login page) - see the signup/login
brainstorm for why this ROPC tradeoff is acceptable for a first-party
frontend.

Idempotent (get_or_create on name) - safe to re-run.

Run:
docker cp data/scripts/create_frontend_oauth_app.py \
  geonode-demo-django-1:/tmp/create_frontend_oauth_app.py
docker exec geonode-demo-django-1 bash -c \
  "cd /usr/src/geonode && python manage.py shell < /tmp/create_frontend_oauth_app.py"
"""

from oauth2_provider.models import get_application_model

Application = get_application_model()

app, created = Application.objects.get_or_create(
    name="geonode-demo-frontend",
    defaults=dict(
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_PASSWORD,
        skip_authorization=True,
    ),
)

print(f"{'created' if created else 'exists'}: {app.name}")
print(f"client_id={app.client_id}")
