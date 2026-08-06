from django.urls import path
from geonode.urls import urlpatterns as geonode_urlpatterns

from accounts_api.views import SignupView
from uploads_api.views import ConvertParquetView, SourceLinkView

urlpatterns = [
    path("api/v2/signup/", SignupView.as_view(), name="accounts_api_signup"),
    path(
        "api/v2/custom/convert-parquet/",
        ConvertParquetView.as_view(),
        name="uploads_api_convert_parquet",
    ),
    path(
        "api/v2/custom/source-link/",
        SourceLinkView.as_view(),
        name="uploads_api_source_link",
    ),
] + geonode_urlpatterns
