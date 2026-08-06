from __future__ import annotations

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client

from nfx.adapters.opencnpj import OpenCnpjResponse
from nfx.audit.models import AuditEvent
from nfx.companies.models import Company, CompanyStatus, EnrichmentStatus, FlowFamily, FlowState
from nfx.companies.services import (
    CompanyCnpjImmutable,
    DuplicateCompanyCnpj,
    InvalidCnpj,
    can_execute_flow,
    create_company,
    deactivate_company,
    mark_first_collection,
    normalize_cnpj,
    request_enrichment,
    set_flow_state,
)
from nfx.identity.models import Role, User
from nfx.identity.services import SessionIdentity


VALID_CNPJ = "11.222.333/0001-81"


def _actor(role: str = Role.ADMINISTRATOR) -> SessionIdentity:
    user = User.objects.create(
        email=f"{role}@example.test",
        name=role,
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    return SessionIdentity(str(user.id), user.email, user.name, user.role)


def _company(actor: SessionIdentity | None = None) -> Company:
    return create_company(
        actor=actor or _actor(),
        cnpj=VALID_CNPJ,
        legal_name="Empresa Sintética Ltda.",
        ip_address="127.0.0.1",
    )


@pytest.mark.django_db
def test_cnpj_is_normalized_validated_and_duplicate_is_rejected_by_constraint() -> None:
    assert normalize_cnpj(VALID_CNPJ) == "11222333000181"
    with pytest.raises(InvalidCnpj):
        normalize_cnpj("11.222.333/0001-80")
    actor = _actor()
    _company(actor)
    with pytest.raises(DuplicateCompanyCnpj):
        create_company(actor=actor, cnpj="11222333000181", legal_name="Outra", ip_address="127.0.0.1")
    assert Company.objects.count() == 1


@pytest.mark.django_db
def test_first_durable_collection_makes_cnpj_immutable() -> None:
    actor = _actor()
    company = _company(actor)
    mark_first_collection(str(company.id))
    from nfx.companies.services import update_company

    with pytest.raises(CompanyCnpjImmutable):
        update_company(
            actor=actor,
            company_id=str(company.id),
            version=Company.objects.get(id=company.id).version,
            legal_name=company.legal_name,
            cnpj="04252011000110",
            ip_address="127.0.0.1",
        )


@pytest.mark.django_db
def test_deactivation_preserves_flow_state_and_reactivation_resumes_it() -> None:
    actor = _actor()
    company = _company(actor)
    company.status = CompanyStatus.ACTIVE
    company.save(update_fields=["status", "updated_at"])
    set_flow_state(
        actor=actor,
        company_id=str(company.id),
        family=FlowFamily.NFE,
        state=FlowState.PAUSED,
        ip_address="127.0.0.1",
    )
    deactivate_company(
        actor=actor, company_id=str(company.id), reason="Pausa operacional", ip_address="127.0.0.1"
    )
    company.refresh_from_db()
    assert company.status == CompanyStatus.DEACTIVATED
    assert company.deactivation_reason == "Pausa operacional"
    assert not can_execute_flow(str(company.id), FlowFamily.NFE, certificate_valid=True)

    from nfx.companies.services import activate_company

    activate_company(actor=actor, company_id=str(company.id), ip_address="127.0.0.1")
    assert can_execute_flow(str(company.id), FlowFamily.NFE, certificate_valid=True) is False
    assert company.flows.get(family=FlowFamily.NFE).state == FlowState.PAUSED
    assert can_execute_flow(str(company.id), FlowFamily.NFSE, certificate_valid=True)


class RecordingOpenCnpj:
    def __init__(self, response: OpenCnpjResponse) -> None:
        self.response = response
        self.calls: list[str] = []

    def fetch(self, cnpj: str) -> OpenCnpjResponse:
        self.calls.append(cnpj)
        return self.response


@pytest.mark.django_db
def test_public_enrichment_only_receives_cnpj_and_failures_are_snapshots() -> None:
    actor = _actor()
    company = _company(actor)
    client = RecordingOpenCnpj(OpenCnpjResponse("success", {"razao_social": "Público"}))
    result = request_enrichment(
        actor=actor, company_id=str(company.id), client=client, ip_address="127.0.0.1"
    )
    assert client.calls == ["11222333000181"]
    assert result.snapshot.status == EnrichmentStatus.SUCCESS
    assert result.snapshot.public_non_authoritative is True
    assert AuditEvent.objects.filter(action="company.enrichment").exists()

    timeout = RecordingOpenCnpj(OpenCnpjResponse("timeout", error_code="tempo"))
    result = request_enrichment(
        actor=actor, company_id=str(company.id), client=timeout, ip_address="127.0.0.1"
    )
    assert result.snapshot.status == EnrichmentStatus.TIMEOUT
    assert Company.objects.get(id=company.id).legal_name == "Empresa Sintética Ltda."

    for response, expected in (
        (OpenCnpjResponse("empty"), EnrichmentStatus.EMPTY),
        (OpenCnpjResponse("not_found"), EnrichmentStatus.NOT_FOUND),
        (OpenCnpjResponse("success", "not-json"), EnrichmentStatus.MALFORMED),
    ):
        result = request_enrichment(
            actor=actor,
            company_id=str(company.id),
            client=RecordingOpenCnpj(response),
            ip_address="127.0.0.1",
        )
        assert result.snapshot.status == expected


@pytest.mark.django_db
def test_company_api_is_restricted_to_admin_and_operator_and_has_no_delete() -> None:
    viewer = _actor(Role.VIEWER)
    client = Client()
    from nfx.identity.models import IdentitySession
    from nfx.identity.services import _digest
    from django.utils import timezone
    from datetime import timedelta

    token = "synthetic-company-session"
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=User.objects.get(id=viewer.user_id),
        revocation_version=1,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    client.cookies["nfx_session"] = token
    assert client.get("/api/companies").status_code == 403
    assert client.delete("/api/companies").status_code == 405
