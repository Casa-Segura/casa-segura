from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.contrib import admin
from django.urls import include, path

from shared.observability.health import health, ready

swagger_url_patterns = [
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]

# Phase 1 routers (EPIC-02 ingestion, EPIC-03 corpus). Each app exposes
# its DRF urls under `<app>.interfaces.api.urls`.
api_v1_url_patterns = [
    path("", include("ingestion.interfaces.api.urls", namespace="ingestion")),
    path("corpus/", include("corpus.interfaces.api.urls", namespace="corpus")),
    path(
        "project-verification/",
        include(
            ("project_verification.interfaces.api.urls", "project_verification"),
            namespace="project_verification",
        ),
    ),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/ready/", ready, name="ready"),
    path("api/v1/schema/", include(swagger_url_patterns)),
    path("api/v1/", include((api_v1_url_patterns, "v1"))),
    path("metrics/", include("django_prometheus.urls")),
]
