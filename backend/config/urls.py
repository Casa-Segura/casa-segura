from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.contrib import admin
from django.urls import include, path

from shared.observability.health import health, ready

swagger_url_patterns = [
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]

url_patterns: list = []


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/ready/", ready, name="ready"),
    path("api/v1/schema/", include(swagger_url_patterns)),
    path("api/v1/", include(url_patterns)),
    path("metrics/", include("django_prometheus.urls")),
]
