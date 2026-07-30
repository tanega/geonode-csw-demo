# Local settings override, mounted read-only into django/celery at
# /opt/geonode-custom (PYTHONPATH) and pointed to via DJANGO_SETTINGS_MODULE.
# Lets us add one app + one URL without patching the geonode/geonode image —
# see docs/iam-option-a-signup.md for why.
import os

from geonode.settings import *  # noqa: F401,F403

INSTALLED_APPS = list(INSTALLED_APPS) + ["accounts_api"]
ROOT_URLCONF = "geonode_demo_urls"

# geonode.settings only exposes an all-or-nothing CORS_ALLOW_ALL_ORIGINS env
# var (docs/step7-endpoints-cors.md); now that the frontend has a stable
# origin (docker-compose `web` service behind Traefik) we narrow to an
# explicit allowlist instead of "*".
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
