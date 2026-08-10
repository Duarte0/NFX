from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from nfx.documents.status import (
    DocumentListParams,
    InvalidDocumentListParams,
    list_document_status,
)
from nfx.identity.policy import Action
from nfx.identity.views import protected


@require_GET
@protected(Action.READ_DOCUMENTS)
def documents(request: HttpRequest) -> JsonResponse:
    try:
        params = DocumentListParams.from_query(request.GET)
    except InvalidDocumentListParams:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    return JsonResponse(list_document_status(params))
