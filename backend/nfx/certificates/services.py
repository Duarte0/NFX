from __future__ import annotations

import math
import os
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import BinaryIO, cast

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import pkcs12
from django.db import IntegrityError, transaction
from django.utils import timezone

from nfx.artifacts.storage import ArtifactStorageService, ObjectStore, object_store_from_environment
from nfx.audit.services import AuditService
from nfx.certificates.models import Certificate, CertificateState
from nfx.collection.models import InitialCollectionRequest
from nfx.companies.models import Company, CompanyStatus
from nfx.companies.services import normalize_cnpj
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity
from nfx.infrastructure.configuration import load_settings

CERTIFICATE_MAX_SIZE_BYTES = 5 * 1024 * 1024
CERTIFICATE_KEY_VERSION = 1
GCM_NONCE_SIZE = 12
_CNPJ_CANDIDATE = re.compile(r"(?<!\d)(?:\d[.\-/\s]?){14}(?!\d)")
_DATA_KEY_AAD = b"nfx-certificate-data-key:v1:"
_PFX_AAD = b"nfx-certificate-pfx:v1:"
_PASSWORD_AAD = b"nfx-certificate-password:v1:"


class CertificateError(ValueError):
    """Safe certificate failure; never includes certificate or password material."""


class CertificateNotFound(CertificateError):
    pass


class CertificateAccessDenied(CertificateError):
    pass


class CertificateTooLarge(CertificateError):
    pass


class CertificateUnreadable(CertificateError):
    pass


class CertificateWrongPassword(CertificateError):
    pass


class CertificateExpired(CertificateError):
    pass


class CertificateCnpjMismatch(CertificateError):
    pass


class CertificateAlreadyAssigned(CertificateError):
    pass


class CertificateStorageFailure(CertificateError):
    pass


@dataclass(frozen=True)
class ParsedCertificate:
    fingerprint_sha256: str
    certificate_cnpj: str
    not_before: datetime
    not_after: datetime


@dataclass(frozen=True)
class EnvelopePayload:
    encrypted_data_key: bytes
    data_key_nonce: bytes
    encrypted_password: bytes
    password_nonce: bytes
    encrypted_pfx: bytes


class EnvelopeCipher:
    """AES-256-GCM data encryption with an externally supplied wrapping key."""

    def __init__(self, master_key: bytes, key_version: int = CERTIFICATE_KEY_VERSION) -> None:
        if len(master_key) != 32:
            raise ValueError("A chave mestre de certificado deve ter 32 bytes.")
        self.master_key = master_key
        self.key_version = key_version

    def encrypt(self, certificate_id: uuid.UUID, pfx: bytes, password: str) -> EnvelopePayload:
        data_key = AESGCM.generate_key(256)
        key_nonce = os.urandom(GCM_NONCE_SIZE)
        aad = _DATA_KEY_AAD + certificate_id.bytes
        wrapped_key = AESGCM(self.master_key).encrypt(key_nonce, data_key, aad)
        pfx_nonce = os.urandom(GCM_NONCE_SIZE)
        encrypted_pfx = pfx_nonce + AESGCM(data_key).encrypt(
            pfx_nonce, pfx, _PFX_AAD + certificate_id.bytes
        )
        password_nonce = os.urandom(GCM_NONCE_SIZE)
        encrypted_password = AESGCM(data_key).encrypt(
            password_nonce,
            password.encode("utf-8"),
            _PASSWORD_AAD + certificate_id.bytes,
        )
        return EnvelopePayload(
            wrapped_key,
            key_nonce,
            encrypted_password,
            password_nonce,
            encrypted_pfx,
        )

    def decrypt(
        self, certificate_id: uuid.UUID, payload: EnvelopePayload
    ) -> tuple[bytearray, bytearray]:
        if len(payload.encrypted_pfx) <= GCM_NONCE_SIZE:
            raise CertificateStorageFailure("Material cifrado do certificado está incompleto.")
        try:
            data_key = AESGCM(self.master_key).decrypt(
                payload.data_key_nonce,
                payload.encrypted_data_key,
                _DATA_KEY_AAD + certificate_id.bytes,
            )
            pfx_nonce = payload.encrypted_pfx[:GCM_NONCE_SIZE]
            pfx = AESGCM(data_key).decrypt(
                pfx_nonce,
                payload.encrypted_pfx[GCM_NONCE_SIZE:],
                _PFX_AAD + certificate_id.bytes,
            )
            password = AESGCM(data_key).decrypt(
                payload.password_nonce,
                payload.encrypted_password,
                _PASSWORD_AAD + certificate_id.bytes,
            )
        except Exception as exc:
            raise CertificateStorageFailure(
                "Não foi possível descriptografar o certificado."
            ) from exc
        finally:
            if "data_key" in locals():
                data_key = b"\x00" * len(data_key)
        return bytearray(pfx), bytearray(password)


@dataclass
class CertificateMaterial:
    pfx: bytearray
    password: bytearray
    fingerprint_sha256: str
    certificate_cnpj: str


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _cnpj_candidates(value: str) -> set[str]:
    candidates: set[str] = set()
    for match in _CNPJ_CANDIDATE.finditer(value):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 14:
            try:
                candidates.add(normalize_cnpj(digits))
            except ValueError:
                pass
    return candidates


def _extract_certificate_cnpj(certificate: x509.Certificate) -> str:
    candidates: set[str] = set()
    for attribute in certificate.subject:
        candidates.update(_cnpj_candidates(str(attribute.value)))
    for extension in certificate.extensions:
        raw = getattr(extension.value, "value", b"")
        if isinstance(raw, bytes):
            candidates.update(_cnpj_candidates(raw.decode("utf-8", errors="ignore")))
    if len(candidates) != 1:
        raise CertificateCnpjMismatch("O CNPJ do certificado não pôde ser associado à empresa.")
    return candidates.pop()


def parse_pfx(pfx: bytes, password: str, *, now: datetime | None = None) -> ParsedCertificate:
    if not password:
        raise CertificateWrongPassword("A senha do certificado é obrigatória.")
    try:
        private_key, certificate, _additional = pkcs12.load_key_and_certificates(
            pfx, password.encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise CertificateWrongPassword(
            "A senha do certificado está incorreta ou o arquivo é ilegível."
        ) from exc
    if private_key is None or certificate is None:
        raise CertificateUnreadable("O arquivo não contém um certificado A1 legível.")
    not_before_value = (
        certificate.not_valid_before_utc
        if hasattr(certificate, "not_valid_before_utc")
        else certificate.not_valid_before
    )
    not_after_value = (
        certificate.not_valid_after_utc
        if hasattr(certificate, "not_valid_after_utc")
        else certificate.not_valid_after
    )
    not_before = _utc(not_before_value)
    not_after = _utc(not_after_value)
    current = _utc(now or timezone.now())
    if not_after <= current:
        raise CertificateExpired("O certificado está expirado.")
    if not_before > not_after:
        raise CertificateUnreadable("As datas de validade do certificado são inválidas.")
    return ParsedCertificate(
        fingerprint_sha256=certificate.fingerprint(hashes.SHA256()).hex(),
        certificate_cnpj=_extract_certificate_cnpj(certificate),
        not_before=not_before,
        not_after=not_after,
    )


def _company(company_id: str, *, lock: bool = False) -> Company:
    queryset = Company.objects.all()
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=company_id)
    except Company.DoesNotExist as exc:
        raise CertificateNotFound("Empresa não encontrada.") from exc


def _require_access(actor: SessionIdentity) -> None:
    if not authorize(actor.role, Action.ADMINISTER_CERTIFICATES, actor_id=actor.user_id):
        raise CertificateAccessDenied("Acesso de certificado necessário.")


def _master_key(master_key: bytes | None) -> bytes:
    return master_key if master_key is not None else load_settings().secrets.certificate_master_key


def _queue_initial_collection(company: Company, certificate: Certificate) -> None:
    if company.status != CompanyStatus.ACTIVE or company.first_collection_at is not None:
        return
    InitialCollectionRequest.objects.get_or_create(
        company=company,
        kind="initial",
        defaults={
            "certificate": certificate,
            "idempotency_key": f"initial:{company.id}",
        },
    )


def add_certificate(
    *,
    actor: SessionIdentity,
    company_id: str,
    pfx: bytes,
    password: str,
    ip_address: str,
    object_store: ObjectStore | None = None,
    master_key: bytes | None = None,
    now: datetime | None = None,
) -> Certificate:
    _require_access(actor)
    if len(pfx) > CERTIFICATE_MAX_SIZE_BYTES:
        raise CertificateTooLarge("O arquivo do certificado excede o limite permitido.")
    parsed = parse_pfx(pfx, password, now=now)
    company = _company(company_id)
    if parsed.certificate_cnpj != company.cnpj:
        raise CertificateCnpjMismatch("O CNPJ do certificado não corresponde à empresa.")
    certificate_id = uuid.uuid4()
    envelope = EnvelopeCipher(_master_key(master_key)).encrypt(certificate_id, pfx, password)
    store = object_store or object_store_from_environment()
    artifact_service = ArtifactStorageService(store, maximum_size=CERTIFICATE_MAX_SIZE_BYTES + 64)  # type: ignore[arg-type]
    certificate: Certificate | None = None
    try:
        with transaction.atomic():
            company = _company(company_id, lock=True)
            if (
                Certificate.objects.filter(
                    fingerprint_sha256=parsed.fingerprint_sha256,
                    state=CertificateState.CURRENT,
                )
                .exclude(company=company)
                .exists()
            ):
                raise CertificateAlreadyAssigned(
                    "Este certificado já está associado a outra empresa."
                )
            certificate = Certificate.objects.create(
                id=certificate_id,
                company=company,
                encrypted_data_key=envelope.encrypted_data_key,
                data_key_nonce=envelope.data_key_nonce,
                encrypted_password=envelope.encrypted_password,
                password_nonce=envelope.password_nonce,
                fingerprint_sha256=parsed.fingerprint_sha256,
                certificate_cnpj=parsed.certificate_cnpj,
                not_before=parsed.not_before,
                not_after=parsed.not_after,
                state=CertificateState.PENDING,
                key_version=CERTIFICATE_KEY_VERSION,
            )
            artifact = artifact_service.begin(
                "certificate-pfx",
                f"certificate:{certificate.id}:pfx",
                "application/octet-stream",
            )
            certificate.artifact = artifact
            certificate.save(update_fields=["artifact", "updated_at"])

        try:
            if certificate.artifact is None:
                raise CertificateStorageFailure("Certificado sem objeto cifrado.")
            artifact_service.transmit(certificate.artifact.pk, [envelope.encrypted_pfx])
        except Exception as exc:
            raise CertificateStorageFailure(
                "Não foi possível armazenar o certificado com integridade."
            ) from exc

        with transaction.atomic():
            certificate = Certificate.objects.select_for_update().get(pk=certificate.id)
            company = Company.objects.select_for_update().get(pk=company_id)
            if (
                Certificate.objects.filter(
                    fingerprint_sha256=parsed.fingerprint_sha256,
                    state=CertificateState.CURRENT,
                )
                .exclude(company=company)
                .exists()
            ):
                raise CertificateAlreadyAssigned(
                    "Este certificado já está associado a outra empresa."
                )
            current = (
                Certificate.objects.select_for_update()
                .filter(company=company, state=CertificateState.CURRENT)
                .exclude(pk=certificate.pk)
            )
            replacing = current.exists()
            current.update(state=CertificateState.REPLACED, replaced_at=timezone.now())
            certificate.state = CertificateState.CURRENT
            certificate.activated_at = timezone.now()
            certificate.save(update_fields=["state", "activated_at", "updated_at"])
            _queue_initial_collection(company, certificate)
            AuditService().append(
                action="certificate.replace" if replacing else "certificate.create",
                entity_type="certificate",
                entity_id=str(certificate.id),
                result="success",
                actor_id=actor.user_id,
                actor_role=actor.role,
                ip_address=ip_address,
                context={
                    "company_id": str(company.id),
                    "certificate_cnpj": certificate.certificate_cnpj,
                    "fingerprint_sha256": certificate.fingerprint_sha256,
                    "not_after": certificate.not_after.isoformat(),
                    "key_version": certificate.key_version,
                },
            )
            return certificate
    except (CertificateError, IntegrityError) as exc:
        if certificate is not None:
            Certificate.objects.filter(pk=certificate.pk, state=CertificateState.PENDING).update(
                state=CertificateState.STORAGE_FAILED, updated_at=timezone.now()
            )
        if isinstance(exc, CertificateError):
            raise
        raise CertificateStorageFailure(
            "Não foi possível concluir a substituição do certificado."
        ) from exc


def certificate_status(certificate: Certificate, *, now: datetime | None = None) -> str:
    if certificate.state == CertificateState.CURRENT:
        current = _utc(now or timezone.now())
        if certificate.not_after <= current:
            return "expirado"
        if certificate.not_before > current:
            return "invalido"
        if certificate.not_after <= current + timedelta(days=30):
            return "proximo_vencimento"
        return "valido"
    status_map: dict[CertificateState, str] = {
        CertificateState.PENDING: "pendente",
        CertificateState.REPLACED: "substituido",
        CertificateState.STORAGE_FAILED: "falha_armazenamento",
    }
    return status_map.get(cast(CertificateState, certificate.state), "invalido")


def days_until_expiry(certificate: Certificate, *, now: datetime | None = None) -> int | None:
    if certificate.state != CertificateState.CURRENT:
        return None
    seconds = (_utc(certificate.not_after) - _utc(now or timezone.now())).total_seconds()
    return max(0, math.ceil(seconds / 86400))


def can_collect(company_id: str, *, now: datetime | None = None) -> bool:
    company = Company.objects.filter(pk=company_id, status=CompanyStatus.ACTIVE).first()
    certificate = (
        Certificate.objects.filter(company_id=company_id, state=CertificateState.CURRENT).first()
        if company
        else None
    )
    return bool(
        certificate and certificate_status(certificate, now=now) in {"valido", "proximo_vencimento"}
    )


def certificate_payload(
    certificate: Certificate | None, *, now: datetime | None = None
) -> dict[str, object] | None:
    if certificate is None:
        return None
    return {
        "id": str(certificate.id),
        "state": certificate.state,
        "status": certificate_status(certificate, now=now),
        "fingerprint_sha256": certificate.fingerprint_sha256,
        "certificate_cnpj": certificate.certificate_cnpj,
        "not_before": certificate.not_before.isoformat(),
        "not_after": certificate.not_after.isoformat(),
        "days_until_expiry": days_until_expiry(certificate, now=now),
        "key_version": certificate.key_version,
        "created_at": certificate.created_at.isoformat(),
        "activated_at": certificate.activated_at.isoformat() if certificate.activated_at else None,
    }


@contextmanager
def certificate_material(
    certificate_id: str | uuid.UUID,
    *,
    object_store: ObjectStore | None = None,
    master_key: bytes | None = None,
) -> Iterator[CertificateMaterial]:
    """Short-lived worker-only material access; callers must use this context."""
    certificate = Certificate.objects.select_related("artifact").get(pk=certificate_id)
    if certificate.state != CertificateState.CURRENT or certificate_status(certificate) not in {
        "valido",
        "proximo_vencimento",
    }:
        raise CertificateError("Certificado não está habilitado para coleta.")
    if certificate.artifact is None:
        raise CertificateStorageFailure("Certificado sem objeto cifrado.")
    artifact_service = ArtifactStorageService(object_store or object_store_from_environment())  # type: ignore[arg-type]
    stream: BinaryIO | None = None
    material: tuple[bytearray, bytearray] | None = None
    try:
        stream = artifact_service.open_verified(certificate.artifact.pk)
        if stream is None:
            raise CertificateStorageFailure("Certificado sem objeto cifrado.")
        encrypted_pfx = stream.read()
        payload = EnvelopePayload(
            encrypted_data_key=bytes(certificate.encrypted_data_key),
            data_key_nonce=bytes(certificate.data_key_nonce),
            encrypted_password=bytes(certificate.encrypted_password),
            password_nonce=bytes(certificate.password_nonce),
            encrypted_pfx=encrypted_pfx,
        )
        material = EnvelopeCipher(_master_key(master_key), certificate.key_version).decrypt(
            certificate.id, payload
        )
        yield CertificateMaterial(
            material[0], material[1], certificate.fingerprint_sha256, certificate.certificate_cnpj
        )
    finally:
        if stream is not None:
            stream.close()
        if material is not None:
            material[0][:] = b"\x00" * len(material[0])
            material[1][:] = b"\x00" * len(material[1])
