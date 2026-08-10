"""Django model registry for NFX domain modules."""

from nfx.artifacts.models import Artifact
from nfx.audit.models import AuditChain, AuditEvent
from nfx.certificates.models import Certificate
from nfx.collection.models import CollectionExecution, InitialCollectionRequest
from nfx.companies.models import Company, CompanyFlow, EnrichmentSnapshot
from nfx.identity.models import IdentitySession, LoginThrottle, User
from nfx.jobs.models import Job, JobPolicy, ProcessHeartbeat

__all__ = [
    "Artifact",
    "AuditChain",
    "AuditEvent",
    "Company",
    "CompanyFlow",
    "EnrichmentSnapshot",
    "Certificate",
    "InitialCollectionRequest",
    "CollectionExecution",
    "IdentitySession",
    "LoginThrottle",
    "User",
    "Job",
    "JobPolicy",
    "ProcessHeartbeat",
]
