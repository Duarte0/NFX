from __future__ import annotations

import hashlib
import io
import re
import zlib
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.companies.models import Company
from nfx.documents.models import Document, DocumentEvidence
from nfx.documents.rendering import (
    PDF_RENDER_JOB_TYPE,
    PINNED_RENDERER_VERSION,
    RENDERER_ID,
    PdfRepresentation,
    render_pdf_bytes,
    render_pdf_job,
    renderer_metadata,
    request_render,
)
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import Role, User
from nfx.identity.services import SessionIdentity
from nfx.jobs.models import Job, JobState
from nfx.jobs.services import JobEngine


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        payload = b"".join(chunks)
        if len(payload) > maximum_size:
            raise ValueError("too large")
        self.objects[object_key] = (payload, content_type)
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def head(self, object_key: str) -> ObjectMetadata | None:
        value = self.objects.get(object_key)
        return (
            None
            if value is None
            else ObjectMetadata(
                len(value[0]), hashlib.sha256(value[0]).hexdigest(), value[1]
            )
        )

    def read(self, object_key: str) -> io.BytesIO | None:
        value = self.objects.get(object_key)
        return None if value is None else io.BytesIO(value[0])

    def list_keys(self, prefix: str) -> Iterator[str]:
        yield from (key for key in self.objects if key.startswith(prefix))

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


DANFSE_FIXTURE = b"""
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFSe12345678901234567890123456789012345678901234567890">
    <nNFSe>123</nNFSe><dhProc>2026-08-11T12:00:00-03:00</dhProc><cStat>100</cStat>
    <xLocEmi>Brasilia</xLocEmi><ambGer>1</ambGer>
    <valores><vLiq>100.00</vLiq><vISSQN>2.00</vISSQN></valores>
  </infNFSe>
  <DPS>
    <infDPS>
      <dCompet>2026-08-11</dCompet><dhEmi>2026-08-11T12:00:00-03:00</dhEmi>
      <tpAmb>2</tpAmb><nDPS>1</nDPS><serie>1</serie><tpEmit>1</tpEmit>
      <serv><cTribNac>010101</cTribNac><xDescServ>Servico sintetico</xDescServ></serv>
      <tribMun><tribISSQN>1</tribISSQN></tribMun>
      <tribFed><tpRetPisCofins>1</tpRetPisCofins><vRetCSLL>1.00</vRetCSLL>
        <vPis>2.00</vPis><vCofins>3.00</vCofins></tribFed>
      <IBSCBS><CST>000</CST><cClassTrib>000001</cClassTrib></IBSCBS>
    </infDPS>
    <prest><CNPJ>11222333000181</CNPJ><xNome>Prestador Sintetico</xNome>
      <end><xLgr>Rua A</xLgr><nro>1</nro><xBairro>Centro</xBairro>
        <cMun>5300108</cMun><CEP>70000000</CEP></end>
    </prest>
  </DPS>
  <emit><CNPJ>11222333000181</CNPJ><xNome>Prestador Sintetico</xNome>
    <enderNac><xLgr>Rua A</xLgr><nro>1</nro><xBairro>Centro</xBairro>
      <cMun>5300108</cMun><CEP>70000000</CEP></enderNac>
  </emit>
</NFSe>
"""

DANFE_FIXTURE = b"""
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe35260811222333000181550010000000011000000010" versao="4.00">
    <ide><cUF>35</cUF><natOp>VENDA</natOp><mod>55</mod><serie>1</serie><nNF>1</nNF>
      <dhEmi>2026-08-11T12:00:00-03:00</dhEmi><tpNF>1</tpNF><idDest>1</idDest>
      <cMunFG>3550308</cMunFG><tpImp>1</tpImp><tpEmis>1</tpEmis><cDV>0</cDV>
      <tpAmb>2</tpAmb><finNFe>1</finNFe><indFinal>1</indFinal><indPres>1</indPres>
      <procEmi>0</procEmi><verProc>synthetic</verProc>
    </ide>
    <emit><CNPJ>11222333000181</CNPJ><xNome>Emitente Sintetico</xNome><xLgr>Rua A</xLgr>
      <nro>1</nro><xBairro>Centro</xBairro><cMun>3550308</cMun><xMun>Sao Paulo</xMun>
      <UF>SP</UF><CEP>01000000</CEP><IE>123</IE><CRT>3</CRT>
    </emit>
    <dest><CNPJ>22333444000181</CNPJ><xNome>Destinatario Sintetico</xNome><xLgr>Rua B</xLgr>
      <nro>2</nro><xBairro>Centro</xBairro><cMun>3550308</cMun><xMun>Sao Paulo</xMun>
      <UF>SP</UF><CEP>01000001</CEP><indIEDest>9</indIEDest>
    </dest>
    <det nItem="1"><prod><cProd>1</cProd><cEAN>SEM GTIN</cEAN><xProd>Produto sintetico</xProd>
      <NCM>01012100</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>1.0000</qCom>
      <vUnCom>10.00</vUnCom><vProd>10.00</vProd><cEANTrib>SEM GTIN</cEANTrib><uTrib>UN</uTrib>
      <qTrib>1.0000</qTrib><vUnTrib>10.00</vUnTrib><indTot>1</indTot></prod>
      <imposto><ICMS><ICMS00><orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>10.00</vBC>
        <pICMS>18.00</pICMS><vICMS>1.80</vICMS></ICMS00></ICMS>
        <PIS><PISAliq><CST>01</CST><vBC>10.00</vBC><pPIS>0</pPIS><vPIS>0</vPIS></PISAliq></PIS>
        <COFINS><COFINSAliq><CST>01</CST><vBC>10.00</vBC><pCOFINS>0</pCOFINS>
          <vCOFINS>0</vCOFINS></COFINSAliq></COFINS>
      </imposto>
    </det>
    <total><ICMSTot><vBC>10.00</vBC><vICMS>1.80</vICMS><vICMSDeson>0</vICMSDeson>
      <vFCP>0</vFCP><vBCST>0</vBCST><vST>0</vST><vFCPST>0</vFCPST><vFCPSTRet>0</vFCPSTRet>
      <vProd>10.00</vProd><vFrete>0</vFrete><vSeg>0</vSeg><vDesc>0</vDesc><vII>0</vII>
      <vIPI>0</vIPI><vIPIDevol>0</vIPIDevol><vPIS>0</vPIS><vCOFINS>0</vCOFINS><vOutro>0</vOutro>
      <vNF>10.00</vNF><vTotTrib>1.80</vTotTrib>
    </ICMSTot></total>
    <transp><modFrete>9</modFrete></transp><pag><detPag><tPag>01</tPag><vPag>10.00</vPag>
    </detPag></pag>
  </infNFe>
</NFe>
"""


def _flate_text(pdf: bytes) -> bytes:
    streams = re.finditer(
        rb"<<.*?/Filter /FlateDecode.*?>>\s*stream\r?\n(.*?)\r?\nendstream", pdf, re.S
    )
    return b"\n".join(zlib.decompress(match.group(1)) for match in streams)


def test_renderer_metadata_is_version_pinned_and_safe() -> None:
    metadata = renderer_metadata()

    assert metadata.renderer_id == RENDERER_ID == "brazilfiscalreport"
    assert metadata.version == PINNED_RENDERER_VERSION == "1.0.1"
    assert metadata.representations == (PdfRepresentation.DANFE, PdfRepresentation.DANFSE)


def test_danfse_uses_only_the_national_representation() -> None:
    assert PdfRepresentation.for_family("nfe") is PdfRepresentation.DANFE
    assert PdfRepresentation.for_family("nfse") is PdfRepresentation.DANFSE


def test_danfse_fixture_covers_nt_geometry_homologation_and_situation_marks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import brazilfiscalreport.danfse.danfse as danfse_module

    qr_call: dict[str, object] = {}
    original_qr = danfse_module.draw_qr_code

    def capture_qr(*args: object, **kwargs: object) -> object:
        qr_call["data"] = args[1]
        qr_call["box_size"] = kwargs["box_size"]
        return original_qr(*args, **kwargs)

    monkeypatch.setattr(danfse_module, "draw_qr_code", capture_qr)
    pdf = render_pdf_bytes(DANFSE_FIXTURE, PdfRepresentation.DANFSE)
    text = _flate_text(pdf)

    assert pdf.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type /Page(?:\s|$)", pdf)) == 1
    assert b"/MediaBox [0 0 595.28 841.89]" in pdf
    assert b"NFS-e SEM VALIDADE" in text
    assert b"TRIBUTA" in text and b"IBS / CBS" in text
    assert b"Contribui" in text and b"Servico sintetico" in text
    assert b"R$ 6,00" in text and b"R$ 0,00" in text
    assert qr_call == {
        "data": "https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave=e12345678901234567890123456789012345678901234567890",
        "box_size": 19,
    }

    cancelled = _flate_text(
        render_pdf_bytes(DANFSE_FIXTURE, PdfRepresentation.DANFSE, cancelled=True)
    )
    replaced = _flate_text(
        render_pdf_bytes(DANFSE_FIXTURE, PdfRepresentation.DANFSE, replaced=True)
    )
    assert b"CANCELADA" in cancelled
    assert b"SUBSTITU" in replaced


def test_danfe_fixture_uses_the_in_process_api() -> None:
    pdf = render_pdf_bytes(DANFE_FIXTURE, PdfRepresentation.DANFE)
    text = _flate_text(pdf)

    assert pdf.startswith(b"%PDF-")
    assert b"/MediaBox [0 0 595.28 841.89]" in pdf
    assert b"Produto sintetico" in text


@pytest.mark.django_db(transaction=True)
def test_request_is_idempotent_and_worker_finalizes_a_verified_derived_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryObjectStore()
    xml = b"<NFe xmlns='urn:synthetic'><infNFe/></NFe>"
    source = Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key="render-source",
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest=hashlib.sha256(xml).hexdigest(),
        size_bytes=len(xml),
        declared_mime_type="application/xml",
        detected_mime_type="application/xml",
        state=ArtifactState.FINALIZED,
    )
    store.objects[source.object_key] = (xml, "application/xml")
    company = Company.objects.create(cnpj="11222333000181", legal_name="Synthetic Renderer")
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family="nfe",
            role="entrada",
            category="document",
            source="simulator",
            flow="distribution",
            identity=FiscalIdentity(official_key="render-doc"),
            emitted_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
            artifact_id=source.id,
            origin_execution_ref="render-test",
        )
    )
    assert result.document_id
    document = Document.objects.get(pk=result.document_id)
    evidence = DocumentEvidence.objects.get(document=document)
    actor_user = User.objects.create(
        email=f"render-{uuid4().hex}@example.test",
        name="Synthetic Renderer",
        role=Role.VIEWER,
        password_hash=make_password("synthetic-password"),
    )
    actor = SessionIdentity(str(actor_user.id), actor_user.email, actor_user.name, actor_user.role)
    monkeypatch.setattr(
        "nfx.documents.rendering.render_pdf_bytes",
        lambda *_args, **_kwargs: b"%PDF-1.7\nsynthetic\n%%EOF\n",
    )

    requested = request_render(actor=actor, document_id=document.id)
    duplicate = request_render(actor=actor, document_id=document.id)

    assert requested.render is not None
    assert duplicate.render is not None
    assert duplicate.render.id == requested.render.id
    job = Job.objects.get(job_type=PDF_RENDER_JOB_TYPE)
    assert job.state == JobState.QUEUED
    claimed = JobEngine().claim("render-worker")
    assert claimed is not None
    outcome = render_pdf_job(
        requested.render.id,
        storage=ArtifactStorageService(store),
        actor_id=actor.user_id,
    )
    assert outcome.kind == "success"
    JobEngine().finalize(claimed.id, "render-worker", outcome)
    render = requested.render.__class__.objects.get(pk=requested.render.id)
    assert render.state == "finalized"
    assert render.artifact_id is not None
    assert render.source_artifact_id == evidence.artifact_id
    assert render.digest == hashlib.sha256(b"%PDF-1.7\nsynthetic\n%%EOF\n").hexdigest()
