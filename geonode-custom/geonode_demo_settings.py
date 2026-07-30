# Local settings override, mounted read-only into django/celery at
# /opt/geonode-custom (PYTHONPATH) and pointed to via DJANGO_SETTINGS_MODULE.
# Lets us add one app + one URL without patching the geonode/geonode image —
# see docs/iam-option-a-signup.md for why.
from geonode.settings import *  # noqa: F401,F403

INSTALLED_APPS = list(INSTALLED_APPS) + ["accounts_api"]
ROOT_URLCONF = "geonode_demo_urls"
