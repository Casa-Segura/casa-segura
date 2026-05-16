"""Smoke test for CS-002: Django boots and the URL conf is importable."""
import pytest


@pytest.mark.django_db
def test_django_setup_works():
    from django.apps import apps
    assert apps.ready, "Django app registry must be ready"


@pytest.mark.django_db
def test_url_conf_loads():
    from django.urls import get_resolver
    resolver = get_resolver()
    assert resolver.url_patterns, "URL patterns must exist"


def test_settings_module_importable():
    import config.settings  # noqa: F401
