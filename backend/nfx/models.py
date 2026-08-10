"""Django model registry for NFX domain modules."""

from nfx.artifacts.models import Artifact
from nfx.audit.models import AuditChain, AuditEvent
from nfx.backup.models import BackupSet, RestoreOperation
from nfx.certificates.models import Certificate
from nfx.collection.models import (
    CollectionExecution,
    IngestionCheckpoint,
    IngestionPage,
    InitialCollectionRequest,
    ReceivedUnit,
)
from nfx.companies.models import Company, CompanyFlow, EnrichmentSnapshot
from nfx.documents.models import Document, DocumentEvent, DocumentEventEvidence, DocumentEvidence
from nfx.identity.models import IdentitySession, LoginThrottle, User
from nfx.jobs.models import Job, JobPolicy, ProcessHeartbeat

__all__ = [
    "Artifact",
    "AuditChain",
    "AuditEvent",
    "BackupSet",
    "RestoreOperation",
    "Company",
    "CompanyFlow",
    "EnrichmentSnapshot",
    "Certificate",
    "InitialCollectionRequest",
    "CollectionExecution",
    "IngestionCheckpoint",
    "IngestionPage",
    "ReceivedUnit",
    "IdentitySession",
    "LoginThrottle",
    "User",
    "Job",
    "JobPolicy",
    "ProcessHeartbeat",
    "Document",
    "DocumentEvidence",
    "DocumentEvent",
    "DocumentEventEvidence",
]
