from django.test import Client


def test_liveness_does_not_need_external_services() -> None:
    response = Client().get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_correlation_id_is_returned() -> None:
    response = Client().get("/health/live", HTTP_X_CORRELATION_ID="synthetic-correlation")
    assert response["X-Correlation-ID"] == "synthetic-correlation"


def test_operational_details_are_restricted_to_system_administrators() -> None:
    response = Client().get("/health/operational")
    assert response.status_code == 403
