"""HMIS integration contracts for 211-AI wallet workflows."""

from .adapters import FileExchangeHmisAdapter, ManualReviewHmisAdapter, VendorApiHmisAdapter
from .audit import HmisAuditStore
from .config import HmisConfig, HmisFeatureFlags, HmisMode, load_hmis_config_from_env
from .consent import HmisConsentDecision, evaluate_hmis_consent
from .errors import (
    HmisAdapterError,
    HmisConfigError,
    HmisConsentError,
    HmisIntegrationError,
    HmisMappingError,
    HmisMatchError,
    HmisPolicyError,
)
from .mapper import HmisFieldMapping, HmisMappingRegistry
from .matching import HmisMatchCandidate, HmisMatchResult, match_hmis_clients, match_hmis_households
from .models import (
    HmisActionType,
    HmisAdapterCapabilities,
    HmisAdapterResult,
    HmisClientLink,
    HmisConsentRecord,
    HmisEnrollmentRecord,
    HmisHouseholdLink,
    HmisProgramLink,
    HmisReferralRecord,
    HmisSyncEvent,
)
from .service import HmisExecutionResult, HmisReconciliationItem, HmisReferralDraftRecord, HmisService

__all__ = [
    "FileExchangeHmisAdapter",
    "HmisActionType",
    "HmisAdapterCapabilities",
    "HmisAdapterError",
    "HmisAdapterResult",
    "HmisAuditStore",
    "HmisClientLink",
    "HmisConfig",
    "HmisConfigError",
    "HmisConsentDecision",
    "HmisConsentError",
    "HmisConsentRecord",
    "HmisEnrollmentRecord",
    "HmisExecutionResult",
    "HmisFeatureFlags",
    "HmisFieldMapping",
    "HmisHouseholdLink",
    "HmisIntegrationError",
    "HmisMappingError",
    "HmisMappingRegistry",
    "HmisMatchCandidate",
    "HmisMatchError",
    "HmisMatchResult",
    "HmisMode",
    "HmisPolicyError",
    "HmisProgramLink",
    "HmisReconciliationItem",
    "HmisReferralDraftRecord",
    "HmisReferralRecord",
    "HmisService",
    "HmisSyncEvent",
    "ManualReviewHmisAdapter",
    "VendorApiHmisAdapter",
    "evaluate_hmis_consent",
    "load_hmis_config_from_env",
    "match_hmis_clients",
    "match_hmis_households",
]
