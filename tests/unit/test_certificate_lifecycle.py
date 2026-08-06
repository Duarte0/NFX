from __future__ import annotations

import hashlib
import io
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.contrib.auth.hashers import make_password
from django.db import connections

from nfx.artifacts.storage import ObjectMetadata
from nfx.audit.models import AuditEvent
from nfx.certificates.models import Certificate, CertificateState
from nfx.certificates.services import (
    CertificateCnpjMismatch,
    CertificateExpired,
    CertificateStorageFailure,
    CertificateWrongPassword,
    add_certificate,
    can_collect,
    certificate_material,
    certificate_status,
)
from nfx.companies.models import Company, CompanyStatus
from nfx.companies.services import create_company
from nfx.collection.models import InitialCollectionRequest
from nfx.identity.models import Role, User
from nfx.identity.services import SessionIdentity


MASTER_KEY = b"\x00" * 32
CNPJ = "11222333000181"
PASSWORD = "synthetic-pfx-password"


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_writes = False

    def write_stream(self, object_key: str, chunks: object, content_type: str, maximum_size: int) -> ObjectMetadata:
        if self.fail_writes:
            raise RuntimeError("synthetic storage outage")
        payload = b"".join(chunks)  # type: ignore[arg-type]
        if len(payload) > maximum_size:
            raise RuntimeError("synthetic limit")
        self.objects[object_key] = (payload, content_type)
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def head(self, object_key: str) -> ObjectMetadata | None:
        value = self.objects.get(object_key)
        if value is None:
            return None
        payload, content_type = value
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def read(self, object_key: str) -> io.BytesIO | None:
        value = self.objects.get(object_key)
        return io.BytesIO(value[0]) if value else None

    def list_keys(self, prefix: str) -> object:
        return iter(key for key in self.objects if key.startswith(prefix))


def _pfx(*, days: int = 365, cnpj: str = CNPJ, password: str = PASSWORD) -> bytes:
    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic A1"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, cnpj),
        ]
    )
    not_before = now - timedelta(days=2) if days < 0 else now - timedelta(minutes=1)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(now + timedelta(days=days))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"synthetic-a1",
        key,
        certificate,
        None,
        serialization.BestAvailableEncryption(password.encode()),
    )


def _actor(role: str = Role.ADMINISTRATOR) -> SessionIdentity:
    user = User.objects.create(
        email=f"{uuid.uuid4()}@example.test",
        name="Synthetic operator",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    return SessionIdentity(str(user.id), user.email, user.name, user.role)


def _company(actor: SessionIdentity | None = None) -> Company:
    company = create_company(
        actor=actor or _actor(),
        cnpj="11.222.333/0001-81",
        legal_name="Synthetic Company Ltda.",
        ip_address="127.0.0.1",
    )
    company.status = CompanyStatus.ACTIVE
    company.save(update_fields=["status", "updated_at"])
    return company


@pytest.mark.django_db
def test_valid_pfx_is_enveloped_and_queues_one_idempotent_initial_request() -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    pfx = _pfx()

    certificate = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=pfx,
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
    )

    artifact = certificate.artifact
    assert certificate.state == CertificateState.CURRENT
    assert artifact is not None
    ciphertext = store.objects[artifact.object_key][0]
    assert pfx not in ciphertext
    assert PASSWORD.encode() not in bytes(certificate.encrypted_password)
    assert InitialCollectionRequest.objects.filter(company=company, kind="initial").count() == 1
    assert AuditEvent.objects.filter(action="certificate.create", entity_id=str(certificate.id)).exists()
    assert can_collect(str(company.id))

    with certificate_material(certificate.id, object_store=store, master_key=MASTER_KEY) as material:
        assert bytes(material.pfx) == pfx
        assert bytes(material.password) == PASSWORD.encode()


@pytest.mark.django_db
def test_invalid_password_and_cnpj_do_not_change_current_certificate() -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    current = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
    )

    with pytest.raises(CertificateWrongPassword):
        add_certificate(
            actor=actor,
            company_id=str(company.id),
            pfx=_pfx(),
            password="wrong-password",
            ip_address="127.0.0.1",
            object_store=store,
            master_key=MASTER_KEY,
        )
    assert Certificate.objects.get(company=company, state=CertificateState.CURRENT).id == current.id

    with pytest.raises(CertificateCnpjMismatch):
        add_certificate(
            actor=actor,
            company_id=str(company.id),
            pfx=_pfx(cnpj="04252011000110"),
            password=PASSWORD,
            ip_address="127.0.0.1",
            object_store=store,
            master_key=MASTER_KEY,
        )
    assert Certificate.objects.filter(company=company, state=CertificateState.CURRENT).count() == 1

    with pytest.raises(CertificateExpired):
        add_certificate(
            actor=actor,
            company_id=str(company.id),
            pfx=_pfx(days=-1),
            password=PASSWORD,
            ip_address="127.0.0.1",
            object_store=store,
            master_key=MASTER_KEY,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("days, expected", [(30, "proximo_vencimento"), (31, "valido")])
def test_expiry_boundary_is_inclusive_at_thirty_days(days: int, expected: str) -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    reference = datetime.now(timezone.utc)
    certificate = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(days=days),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
        now=reference,
    )
    assert certificate_status(certificate, now=reference) == expected


@pytest.mark.django_db
def test_current_certificate_becomes_expired_and_blocks_collection() -> None:
    actor = _actor()
    company = _company(actor)
    reference = datetime.now(timezone.utc)
    certificate = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=MemoryObjectStore(),
        master_key=MASTER_KEY,
        now=reference,
    )
    certificate.not_after = reference - timedelta(seconds=1)
    certificate.save(update_fields=["not_after", "updated_at"])
    certificate.refresh_from_db()
    assert certificate_status(certificate, now=reference) == "expirado"
    assert not can_collect(str(company.id), now=reference)


@pytest.mark.django_db
def test_replacement_preserves_history_and_wrong_envelope_key_fails() -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    first = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
    )
    second = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
    )

    first.refresh_from_db()
    assert first.state == CertificateState.REPLACED
    assert second.state == CertificateState.CURRENT
    assert Certificate.objects.filter(company=company, state=CertificateState.CURRENT).count() == 1
    assert InitialCollectionRequest.objects.filter(company=company).count() == 1
    with pytest.raises(CertificateStorageFailure):
        with certificate_material(second.id, object_store=store, master_key=b"\x01" * 32):
            pass


@pytest.mark.django_db(transaction=True)
def test_concurrent_replacements_leave_exactly_one_current_certificate() -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    barrier = threading.Barrier(2)
    certificates: list[Certificate] = []
    failures: list[BaseException] = []

    def replace() -> None:
        try:
            barrier.wait()
            certificates.append(
                add_certificate(
                    actor=actor,
                    company_id=str(company.id),
                    pfx=_pfx(),
                    password=PASSWORD,
                    ip_address="127.0.0.1",
                    object_store=store,
                    master_key=MASTER_KEY,
                )
            )
        except BaseException as exc:  # pragma: no cover - asserted by caller
            failures.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=replace) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not failures
    assert len(certificates) == 2
    assert Certificate.objects.filter(company=company, state=CertificateState.CURRENT).count() == 1
    assert Certificate.objects.filter(company=company, state=CertificateState.REPLACED).count() == 1


@pytest.mark.django_db
def test_storage_failure_leaves_no_current_change_and_is_retryable() -> None:
    actor = _actor()
    company = _company(actor)
    store = MemoryObjectStore()
    current = add_certificate(
        actor=actor,
        company_id=str(company.id),
        pfx=_pfx(),
        password=PASSWORD,
        ip_address="127.0.0.1",
        object_store=store,
        master_key=MASTER_KEY,
    )
    store.fail_writes = True
    with pytest.raises(CertificateStorageFailure):
        add_certificate(
            actor=actor,
            company_id=str(company.id),
            pfx=_pfx(),
            password=PASSWORD,
            ip_address="127.0.0.1",
            object_store=store,
            master_key=MASTER_KEY,
        )
    assert Certificate.objects.get(company=company, state=CertificateState.CURRENT).id == current.id
