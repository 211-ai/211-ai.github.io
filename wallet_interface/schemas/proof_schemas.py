"""Wallet interface request schemas."""

from __future__ import annotations

from typing import Any

from .base import BaseModel, Field


class CoarseLocationGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    expires_at: str | None = None


class CoarseLocationInvocationRequest(BaseModel):
    grant_id: str
    actor_did: str
    actor_key_hex: str | None = None
    expires_at: str | None = None
    purpose: str | None = None
    user_present: bool = False


class LocationRegionProofGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    expires_at: str | None = None


class LocationRegionProofRequest(BaseModel):
    actor_did: str
    region_id: str
    grant_id: str | None = None


class LocationDistanceProofGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    target_id: str
    max_distance_km: float
    expires_at: str | None = None


class LocationDistanceProofRequest(BaseModel):
    actor_did: str
    target_id: str
    target_lat: float
    target_lon: float
    max_distance_km: float
    grant_id: str | None = None


class DocumentPrivacyProfileProofRequest(BaseModel):
    actor_did: str
    public_inputs: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CoarseLocationGrantRequest",
    "CoarseLocationInvocationRequest",
    "LocationRegionProofGrantRequest",
    "LocationRegionProofRequest",
    "LocationDistanceProofGrantRequest",
    "LocationDistanceProofRequest",
    "DocumentPrivacyProfileProofRequest",
]
