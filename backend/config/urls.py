from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.contrib import admin
from django.urls import include, path


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


swagger_url_patterns = [
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]

url_patterns: list = []


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check),
    path("api/v1/schema/", include(swagger_url_patterns)),
    path("api/v1/", include(url_patterns)),
    path("metrics/", include("django_prometheus.urls")),
]
