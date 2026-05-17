"""SMS registry smoke — CS-239."""

from delivery.domain.sms_templates import SMS_TEMPLATE_REGISTRY_VERSION, validate_registry_strings_loaded


def test_sms_registry_version_bumped():
    assert SMS_TEMPLATE_REGISTRY_VERSION


def test_sms_registry_validator():
    validate_registry_strings_loaded()
