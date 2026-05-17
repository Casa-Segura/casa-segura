from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.contrib import admin
from django.urls import include, path

from delivery.interfaces.public_views import PublicReportHtmlView
from shared.observability.health import health, ready

swagger_url_patterns = [
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]

# Phase 1 routers (EPIC-02 ingestion, EPIC-03 corpus). Each app exposes
# its DRF urls under `<app>.interfaces.api.urls`.
api_v1_url_patterns = [
    path("", include("ingestion.interfaces.api.urls", namespace="ingestion")),
    path("webhooks/zavu/", include("delivery.interfaces.api.urls")),
    path("corpus/", include("corpus.interfaces.api.urls", namespace="corpus")),
    path(
        "project-verification/",
        include(
            ("project_verification.interfaces.api.urls", "project_verification"),
            namespace="project_verification",
        ),
    ),
]


# Internal-only QA / eval surface (EPIC-04 PR-6). Gated by IsInternal
# (shared-secret header X-Internal-Token vs settings.INTERNAL_API_TOKEN).
api_v1_internal_url_patterns = [
    path(
        "",
        include(
            ("classification.interfaces.api.urls", "classification"),
            namespace="classification",
        ),
    ),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("r/<str:public_short_id>/", PublicReportHtmlView.as_view(), name="public-report-html"),
    path("api/health/", health, name="health"),
    path("api/ready/", ready, name="ready"),
    path("api/v1/schema/", include(swagger_url_patterns)),
    path("api/v1/", include((api_v1_url_patterns, "v1"))),
    path("api/v1/internal/", include((api_v1_internal_url_patterns, "v1_internal"))),
    path("metrics/", include("django_prometheus.urls")),
]
