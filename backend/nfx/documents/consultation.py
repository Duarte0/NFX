"""Bounded, read-only document consultation primitives.

This module owns request validation and safe values used by the HTTP read
boundary. Document identity and artifact bytes remain owned by their modules.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.core import signing
from django.db.models import F, Prefetch

from nfx.artifacts.models import Artifact, ArtifactState
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEventEvidence,
    DocumentEvidence,
)

_ALLOWED_KEYS = frozenset(
    {
        "company_id",
        "competence_from",
        "competence_to",
        "emitted_from",
        "emitted_to",
        "family",
        "flow",
        "direction",
        "nfse_category",
        "event_type",
        "search",
        "limit",
        "cursor",
    }
)
_FAMILIES = frozenset(("nfe", "nfse"))
_DIRECTIONS = frozenset(("entrada", "saida"))
_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_.:/-]{1,64}$")
_CURSOR_SALT = "nfx.documents.consultation.cursor"
_MAX_COMPANIES = 20
_MAX_LIMIT = 100


class InvalidConsultationParams(ValueError):
    """The public consultation query is invalid or exceeds its bounds."""


@dataclass(frozen=True)
class ConsultationParams:
    company_ids: tuple[UUID, ...] = ()
    competence_from: date | None = None
    competence_to: date | None = None
    emitted_from: date | None = None
    emitted_to: date | None = None
    family: str | None = None
    flow: str | None = None
    direction: str | None = None
    nfse_category: str | None = None
    event_type: str | None = None
    search: str | None = None
    limit: int = 50
    cursor: str | None = None


def _values(query: Mapping[str, object], key: str) -> list[object]:
    getlist = getattr(query, "getlist", None)
    if callable(getlist):
        return list(getlist(key))
    value = query.get(key)
    if isinstance(value, list | tuple):
        return list(value)
    return [] if value is None else [value]


def _single(query: Mapping[str, object], key: str) -> object | None:
    values = _values(query, key)
    if len(values) > 1:
        raise InvalidConsultationParams("parameter is repeated")
    return values[0] if values else None


def _text(value: object | None, *, max_length: int, allow_empty: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidConsultationParams("parameter is invalid")
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = " ".join(normalized.split())
    if not normalized and not allow_empty:
        raise InvalidConsultationParams("parameter is invalid")
    if len(normalized) > max_length or any(ord(character) < 32 for character in normalized):
        raise InvalidConsultationParams("parameter is invalid")
    return normalized or None


def _reference(value: object | None) -> str | None:
    result = _text(value, max_length=64)
    if result is not None and not _SAFE_REFERENCE.fullmatch(result):
        raise InvalidConsultationParams("reference is invalid")
    return result


def _date(value: object | None) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidConsultationParams("date is invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidConsultationParams("date is invalid") from exc


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise InvalidConsultationParams("identifier is invalid")
    try:
        return UUID(value)
    except ValueError as exc:
        raise InvalidConsultationParams("identifier is invalid") from exc


def cursor_for(value: str | UUID) -> str:
    """Sign a UUID cursor so database identifiers are not exposed to clients."""
    return signing.Signer(salt=_CURSOR_SALT).sign(str(value))


def _cursor(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidConsultationParams("cursor is invalid")
    try:
        unsigned = signing.Signer(salt=_CURSOR_SALT).unsign(value)
        UUID(unsigned)
    except (signing.BadSignature, ValueError) as exc:
        raise InvalidConsultationParams("cursor is invalid") from exc
    return unsigned


def parse_consultation_params(query: Mapping[str, object]) -> ConsultationParams:
    unknown = set(query.keys()) - _ALLOWED_KEYS
    if unknown:
        raise InvalidConsultationParams("unsupported filter")

    company_values = _values(query, "company_id")
    if len(company_values) > _MAX_COMPANIES:
        raise InvalidConsultationParams("too many companies")
    company_ids = tuple(_uuid(value) for value in company_values)
    family = _text(_single(query, "family"), max_length=8)
    if family is not None and family not in _FAMILIES:
        raise InvalidConsultationParams("family is invalid")
    direction = _text(_single(query, "direction"), max_length=16)
    if direction is not None and direction not in _DIRECTIONS:
        raise InvalidConsultationParams("direction is invalid")
    flow = _reference(_single(query, "flow"))
    nfse_category = _reference(_single(query, "nfse_category"))
    event_type = _reference(_single(query, "event_type"))
    limit_value = _single(query, "limit")
    if limit_value is None:
        limit = 50
    else:
        try:
            limit = int(str(limit_value))
        except (TypeError, ValueError) as exc:
            raise InvalidConsultationParams("limit is invalid") from exc
        if not 1 <= limit <= _MAX_LIMIT:
            raise InvalidConsultationParams("limit is invalid")

    dates = {
        key: _date(_single(query, key))
        for key in ("competence_from", "competence_to", "emitted_from", "emitted_to")
    }
    for start, end in (("competence_from", "competence_to"), ("emitted_from", "emitted_to")):
        start_date = dates[start]
        end_date = dates[end]
        if start_date is not None and end_date is not None and start_date > end_date:
            raise InvalidConsultationParams("date interval is invalid")

    return ConsultationParams(
        company_ids=company_ids,
        competence_from=dates["competence_from"],
        competence_to=dates["competence_to"],
        emitted_from=dates["emitted_from"],
        emitted_to=dates["emitted_to"],
        family=family,
        flow=flow,
        direction=direction,
        nfse_category=nfse_category,
        event_type=event_type,
        search=_text(_single(query, "search"), max_length=128),
        limit=limit,
        cursor=_cursor(_single(query, "cursor")),
    )


def safe_filename(identity: str, content_type: str | None) -> str:
    """Build a short ASCII filename from an untrusted fiscal identity."""
    normalized = unicodedata.normalize("NFKD", identity).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", normalized).strip(".-").lower()[:80]
    normalized = normalized or "document"
    extension = ".xml" if content_type == "application/xml" else ".bin"
    return f"{normalized}{extension}"


def artifact_available(
    artifact: Artifact, *, digest: str, size_bytes: int, conflicting: bool
) -> bool:
    return (
        not conflicting
        and artifact.state == ArtifactState.FINALIZED
        and artifact.digest == digest
        and artifact.size_bytes == size_bytes
    )


def _artifact_payload(
    artifact: Artifact, *, digest: str, size_bytes: int, conflicting: bool
) -> dict[str, object]:
    available = artifact_available(
        artifact, digest=digest, size_bytes=size_bytes, conflicting=conflicting
    )
    return {
        "id": str(artifact.id),
        "digest_prefix": digest[:16],
        "size_bytes": size_bytes,
        "content_type": artifact.detected_mime_type or artifact.declared_mime_type,
        "availability": "available" if available else "unavailable",
    }


def document_detail(document_id: UUID) -> dict[str, object] | None:
    evidence = DocumentEvidence.objects.select_related("artifact").order_by("created_at")
    event_evidence = DocumentEventEvidence.objects.select_related("artifact").order_by("created_at")
    events = DocumentEvent.objects.prefetch_related(
        Prefetch("evidence", queryset=event_evidence)
    ).order_by("occurred_at", "id")
    document = (
        Document.objects.select_related("company")
        .prefetch_related(
            Prefetch("evidence", queryset=evidence), Prefetch("events", queryset=events)
        )
        .filter(pk=document_id)
        .first()
    )
    if document is None:
        return None
    document_evidence = [
        _artifact_payload(
            row.artifact,
            digest=row.digest,
            size_bytes=row.size_bytes,
            conflicting=row.conflicting,
        )
        for row in document.evidence.all()
    ]
    event_rows: list[dict[str, object]] = []
    for event in document.events.all():
        event_rows.append(
            {
                "id": str(event.id),
                "family": event.family,
                "category": event.category,
                "source": event.source,
                "flow": event.flow,
                "identity": event.normalized_identity,
                "occurred_at": event.occurred_at.isoformat(),
                "situation": event.situation,
                "relationship_type": event.relationship_type,
                "state": event.state,
                "artifacts": [
                    _artifact_payload(
                        row.artifact,
                        digest=row.digest,
                        size_bytes=row.size_bytes,
                        conflicting=row.conflicting,
                    )
                    for row in event.evidence.all()
                ],
            }
        )
    available = [row for row in document_evidence if row["availability"] == "available"]
    xml_available = any(row["content_type"] == "application/xml" for row in available)
    return {
        "id": str(document.id),
        "company": {"id": str(document.company_id), "name": document.company.legal_name},
        "family": document.family,
        "role": document.role,
        "category": document.category,
        "source": document.source,
        "flow": document.flow,
        "identity": {"kind": document.identity_kind, "value": document.normalized_identity},
        "dates": {
            "emitted_at": document.emitted_at.isoformat(),
            "authorized_at": document.authorized_at.isoformat() if document.authorized_at else None,
            "competence": document.competence.isoformat(),
        },
        "situation": document.situation,
        "state": document.state,
        "collection": {"origin_execution_ref": document.origin_execution_ref},
        "parties": {"issuer": None, "recipient": None, "provider": None},
        "value_total": None,
        "artifacts": document_evidence,
        "events": event_rows,
        "availability": {
            "xml": xml_available,
            "original": bool(available),
            "pdf": False,
        },
        "download_url": f"/api/documents/{document.id}/download",
    }


def downloadable_artifact(
    *, document_id: UUID | None = None, artifact_id: UUID | None = None
) -> tuple[Document, Artifact] | None:
    evidence = DocumentEvidence.objects.select_related("document", "artifact", "document__company")
    event_evidence = DocumentEventEvidence.objects.select_related(
        "event__parent_document", "event__parent_document__company", "artifact"
    )
    if artifact_id is not None:
        row = evidence.filter(
            artifact_id=artifact_id,
            conflicting=False,
            digest=F("artifact__digest"),
            size_bytes=F("artifact__size_bytes"),
        ).first()
        if row is not None:
            return row.document, row.artifact
        event_row = event_evidence.filter(
            artifact_id=artifact_id,
            conflicting=False,
            digest=F("artifact__digest"),
            size_bytes=F("artifact__size_bytes"),
        ).first()
        if event_row is not None:
            return event_row.event.parent_document, event_row.artifact
        return None
    if document_id is None:
        return None
    row = evidence.filter(
        document_id=document_id,
        conflicting=False,
        digest=F("artifact__digest"),
        size_bytes=F("artifact__size_bytes"),
    ).order_by("created_at").first()
    return (row.document, row.artifact) if row is not None else None
