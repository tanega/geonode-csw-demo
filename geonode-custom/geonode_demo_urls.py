from django.urls import path
from geonode.urls import urlpatterns as geonode_urlpatterns

from accounts_api.views import SignupView

urlpatterns = [
    path("api/v2/signup/", SignupView.as_view(), name="accounts_api_signup"),
] + geonode_urlpatterns
