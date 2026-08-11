from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import cast
from uuid import UUID

from django.db.models import QuerySet

from nfx.artifacts.models import ArtifactState
from nfx.collection.models import (
    CollectionExecutionState,
    IngestionOutcome,
    IngestionPage,
    IngestionPageState,
    ReceivedUnit,
    ReceivedUnitState,
)
from nfx.companies.models import CompanyFlow
from nfx.documents.consultation import (
    InvalidConsultationParams,
    cursor_for,
    parse_consultation_params,
)
from nfx.documents.models import Document, DocumentFamily
from nfx.documents.rendering import render_payload

_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_.:/-]{1,64}$")
_FAMILIES = frozenset(("nfe", "nfse"))


class InvalidDocumentListParams(ValueError):
    """A client parameter is invalid or exceeds the bounded read contract."""


class DocumentStatusCode(StrEnum):
    AVAILABLE = "available"
    VALID_EMPTY = "valid_empty"
    UNAVAILABLE = "unavailable"
    NO_COVERAGE = "no_coverage"
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    RETRY = "retry"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CollectionStatus:
    code: DocumentStatusCode
    reason_code: str


@dataclass(frozen=True)
class DocumentListParams:
    company_id: UUID | None = None
    company_ids: tuple[UUID, ...] = ()
    family: str | None = None
    flow: str | None = None
    competence_from: date | None = None
    competence_to: date | None = None
    emitted_from: date | None = None
    emitted_to: date | None = None
    direction: str | None = None
    nfse_category: str | None = None
    event_type: str | None = None
    search: str | None = None
    limit: int = 50
    cursor: UUID | None = None

    @classmethod
    def from_query(cls, query: Mapping[str, str]) -> DocumentListParams:
        try:
            params = parse_consultation_params(query)
        except InvalidConsultationParams as exc:
            raise InvalidDocumentListParams("document query is invalid") from exc
        cursor = UUID(params.cursor) if params.cursor else None
        company_id = params.company_ids[0] if len(params.company_ids) == 1 else None
        return cls(
            company_id=company_id,
            company_ids=params.company_ids,
            family=params.family,
            flow=params.flow,
            competence_from=params.competence_from,
            competence_to=params.competence_to,
            emitted_from=params.emitted_from,
            emitted_to=params.emitted_to,
            direction=params.direction,
            nfse_category=params.nfse_category,
            event_type=params.event_type,
            search=params.search,
            limit=params.limit,
            cursor=cursor,
        )


def _uuid_parameter(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidDocumentListParams("identifier is invalid") from exc


def collection_status(
    *,
    collection_state: str,
    page_coverage: str | None,
    page_state: str | None,
    has_documents: bool,
    page_outcome: str | None = None,
) -> CollectionStatus:
    """Map existing durable collection/page states without creating frontend state."""
    if page_outcome == IngestionOutcome.NO_COVERAGE:
        return CollectionStatus(DocumentStatusCode.NO_COVERAGE, "coverage_none")
    if page_outcome == IngestionOutcome.UNAVAILABLE:
        return CollectionStatus(DocumentStatusCode.UNAVAILABLE, "source_unavailable")
    if page_outcome in {
        IngestionOutcome.TEMPORARY_FAILURE,
        IngestionOutcome.COOLDOWN,
    }:
        return CollectionStatus(DocumentStatusCode.RETRY, "collection_retry")
    if page_outcome == IngestionOutcome.PARTIAL:
        return CollectionStatus(DocumentStatusCode.PARTIAL, "collection_partial")
    if page_outcome == IngestionOutcome.PERMANENT_FAILURE:
        return CollectionStatus(DocumentStatusCode.BLOCKED, "collection_blocked")
    if page_outcome == IngestionOutcome.MALFORMED:
        return CollectionStatus(DocumentStatusCode.UNKNOWN, "payload_quarantine")
    if page_outcome == IngestionOutcome.QUARANTINE:
        return CollectionStatus(DocumentStatusCode.UNKNOWN, "quarantine_review")
    if page_outcome == IngestionOutcome.CONFLICT:
        return CollectionStatus(DocumentStatusCode.UNKNOWN, "conflict_review")
    if collection_state == CollectionExecutionState.BLOCKED:
        return CollectionStatus(DocumentStatusCode.BLOCKED, "collection_blocked")
    if collection_state in {
        CollectionExecutionState.PARTIAL,
        IngestionPageState.PARTIAL,
    } or page_state == IngestionPageState.PARTIAL:
        return CollectionStatus(DocumentStatusCode.PARTIAL, "collection_partial")
    if collection_state in {
        CollectionExecutionState.RETRYING,
        CollectionExecutionState.COOLDOWN,
    }:
        return CollectionStatus(DocumentStatusCode.RETRY, "collection_retry")
    if page_state == IngestionPageState.FAILED:
        return CollectionStatus(DocumentStatusCode.UNAVAILABLE, "collection_unavailable")
    if page_coverage == "none":
        return CollectionStatus(DocumentStatusCode.NO_COVERAGE, "coverage_none")
    if page_coverage == "unknown":
        return CollectionStatus(DocumentStatusCode.UNKNOWN, "coverage_unknown")
    if collection_state == CollectionExecutionState.FAILED:
        return CollectionStatus(DocumentStatusCode.UNAVAILABLE, "collection_unavailable")
    if page_state is None:
        return CollectionStatus(DocumentStatusCode.UNKNOWN, "not_yet_covered")
    if has_documents:
        return CollectionStatus(DocumentStatusCode.AVAILABLE, "documents_available")
    if collection_state == CollectionExecutionState.EMPTY or page_state == IngestionPageState.EMPTY:
        return CollectionStatus(DocumentStatusCode.VALID_EMPTY, "query_valid_empty")
    if page_state == IngestionPageState.COMPLETE:
        return CollectionStatus(DocumentStatusCode.VALID_EMPTY, "query_valid_empty")
    return CollectionStatus(DocumentStatusCode.UNKNOWN, "collection_unknown")


def _scoped_documents(params: DocumentListParams) -> QuerySet[Document]:
    queryset = (
        Document.objects.select_related("company")
        .prefetch_related("evidence__artifact")
        .order_by("id")
    )
    if params.company_ids:
        queryset = queryset.filter(company_id__in=params.company_ids)
    elif params.company_id:
        queryset = queryset.filter(company_id=params.company_id)
    if params.family:
        queryset = queryset.filter(family=params.family)
    if params.flow:
        queryset = queryset.filter(flow=params.flow)
    if params.competence_from:
        queryset = queryset.filter(competence__gte=params.competence_from)
    if params.competence_to:
        queryset = queryset.filter(competence__lte=params.competence_to)
    if params.emitted_from:
        queryset = queryset.filter(emitted_at__date__gte=params.emitted_from)
    if params.emitted_to:
        queryset = queryset.filter(emitted_at__date__lte=params.emitted_to)
    if params.direction:
        queryset = queryset.filter(family=DocumentFamily.NFE, role=params.direction)
    if params.nfse_category:
        queryset = queryset.filter(family=DocumentFamily.NFSE, category=params.nfse_category)
    if params.event_type:
        queryset = queryset.filter(events__category=params.event_type).distinct()
    if params.search:
        from django.db.models import Q

        queryset = queryset.filter(
            Q(normalized_identity__icontains=params.search)
            | Q(identity_kind__icontains=params.search)
            | Q(role__icontains=params.search)
            | Q(category__icontains=params.search)
            | Q(source__icontains=params.search)
            | Q(flow__icontains=params.search)
            | Q(company__legal_name__icontains=params.search)
        )
    if params.cursor:
        queryset = queryset.filter(id__gt=params.cursor)
    return queryset


def scoped_documents(params: DocumentListParams) -> QuerySet[Document]:
    """Return the canonical P7 document selection for read-only consumers."""
    return _scoped_documents(params)


def _scoped_quarantine(params: DocumentListParams) -> QuerySet[ReceivedUnit]:
    queryset = ReceivedUnit.objects.select_related("company").filter(
        state=ReceivedUnitState.QUARANTINE, document__isnull=True
    ).order_by("id")
    if params.company_ids:
        queryset = queryset.filter(company_id__in=params.company_ids)
    elif params.company_id:
        queryset = queryset.filter(company_id=params.company_id)
    if params.family:
        queryset = queryset.filter(family=params.family)
    if params.flow:
        queryset = queryset.filter(flow=params.flow)
    if params.search:
        queryset = queryset.filter(identity__icontains=params.search)
    if params.cursor:
        queryset = queryset.filter(id__gt=params.cursor)
    return queryset


def _document_payload(document: Document) -> dict[str, object]:
    pdf = render_payload(document)
    return {
        "id": str(document.id),
        "company_id": str(document.company_id),
        "company_name": document.company.legal_name,
        "family": document.family,
        "role": document.role,
        "category": document.category,
        "source": document.source,
        "flow": document.flow,
        "identity": document.normalized_identity,
        "identity_kind": document.identity_kind,
        "emitted_at": document.emitted_at.isoformat(),
        "authorized_at": document.authorized_at.isoformat() if document.authorized_at else None,
        "competence": document.competence.isoformat(),
        "situation": document.situation,
        "outcome": document.state,
        "evidence_available": any(
            evidence.artifact.state == ArtifactState.FINALIZED
            and evidence.digest == evidence.artifact.digest
            and evidence.size_bytes == evidence.artifact.size_bytes
            and not evidence.conflicting
            for evidence in document.evidence.all()
        ),
        "xml_available": any(
            evidence.artifact.state == ArtifactState.FINALIZED
            and (
                evidence.artifact.detected_mime_type in {"application/xml", "text/xml"}
                or evidence.artifact.declared_mime_type in {"application/xml", "text/xml"}
            )
            and not evidence.conflicting
            for evidence in document.evidence.all()
        ),
        "pdf_available": pdf["state"] == "available",
        "pdf_state": pdf["state"],
        "pdf_error": pdf.get("safe_error"),
        "detail_url": f"/api/documents/{document.id}",
        "download_url": f"/api/documents/{document.id}/download",
        "reason_code": "content_hash_mismatch" if document.state == "conflict" else None,
    }


def _quarantine_payload(unit: ReceivedUnit) -> dict[str, object]:
    return {
        "id": str(unit.id),
        "company_id": str(unit.company_id),
        "company_name": unit.company.legal_name,
        "family": unit.family,
        "role": None,
        "category": unit.kind,
        "source": None,
        "flow": unit.flow,
        "identity": unit.identity,
        "identity_kind": None,
        "emitted_at": None,
        "authorized_at": None,
        "competence": None,
        "situation": None,
        "outcome": "quarantine",
        "evidence_available": unit.artifact_id is not None,
        "reason_code": unit.safe_reason or "quarantined",
    }


def _scope_statuses(params: DocumentListParams) -> list[dict[str, object]]:
    flows = CompanyFlow.objects.order_by("company_id", "family")
    if params.company_ids:
        flows = flows.filter(company_id__in=params.company_ids)
    elif params.company_id:
        flows = flows.filter(company_id=params.company_id)
    if params.family:
        flows = flows.filter(family=params.family)
    flow_rows = list(flows[:100])
    statuses: list[dict[str, object]] = []
    for flow_row in flow_rows:
        pages = IngestionPage.objects.filter(
            company_id=flow_row.company_id, family=flow_row.family
        ).order_by("-created_at")
        if params.flow:
            pages = pages.filter(flow=params.flow)
        page = pages.first()
        page_coverage = page.coverage if page else None
        page_state = page.state if page else None
        scoped_documents = Document.objects.filter(
            company_id=flow_row.company_id, family=flow_row.family
        )
        if params.flow:
            scoped_documents = scoped_documents.filter(flow=params.flow)
        status = collection_status(
            collection_state=flow_row.collection_state,
            page_coverage=page_coverage,
            page_state=page_state,
            has_documents=scoped_documents.exists(),
            page_outcome=page.outcome if page else None,
        )
        statuses.append(
            {
                "company_id": str(flow_row.company_id),
                "family": flow_row.family,
                "flow": params.flow,
                "status": status.code,
                "reason_code": status.reason_code,
            }
        )
    if not statuses:
        statuses.append(
            {
                "company_id": str(params.company_id) if params.company_id else None,
                "family": params.family,
                "flow": params.flow,
                "status": DocumentStatusCode.NO_COVERAGE,
                "reason_code": "flow_not_configured",
            }
        )
    return statuses


def _aggregate_status(statuses: list[dict[str, object]]) -> CollectionStatus:
    priority = (
        DocumentStatusCode.BLOCKED,
        DocumentStatusCode.RETRY,
        DocumentStatusCode.PARTIAL,
        DocumentStatusCode.UNAVAILABLE,
        DocumentStatusCode.NO_COVERAGE,
        DocumentStatusCode.UNKNOWN,
        DocumentStatusCode.AVAILABLE,
        DocumentStatusCode.VALID_EMPTY,
    )
    codes = {DocumentStatusCode(cast(str, item["status"])) for item in statuses}
    for code in priority:
        if code in codes:
            reason = next(str(item["reason_code"]) for item in statuses if item["status"] == code)
            return CollectionStatus(code, reason)
    return CollectionStatus(DocumentStatusCode.UNKNOWN, "collection_unknown")


def list_document_status(params: DocumentListParams) -> dict[str, object]:
    documents = list(_scoped_documents(params)[: params.limit + 1])
    quarantined = list(_scoped_quarantine(params)[: params.limit + 1])
    rows = [_document_payload(row) for row in documents] + [
        _quarantine_payload(row) for row in quarantined
    ]
    rows.sort(key=lambda item: (str(item["id"]), str(item["outcome"])))
    page_rows = rows[: params.limit]
    statuses = _scope_statuses(params)
    aggregate = _aggregate_status(statuses)
    return {
        "status": aggregate.code,
        "reason_code": aggregate.reason_code,
        "collection_states": statuses,
        "documents": page_rows,
        "next_cursor": (
            cursor_for(str(page_rows[-1]["id"])) if len(rows) > params.limit else None
        ),
    }
