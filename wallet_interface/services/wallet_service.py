"""Wallet CRUD and governance helpers for WalletInterfaceService."""

from __future__ import annotations

from collections.abc import Sequence


class WalletDomainServiceMixin:
    def create_wallet(
        self,
        owner_did: str,
        *,
        controller_dids: Sequence[str] | None = None,
        approval_threshold: int | None = None,
    ):
        governance_policy = None
        if approval_threshold is not None:
            controllers = list(controller_dids or [owner_did])
            if owner_did not in controllers:
                controllers = [owner_did, *controllers]
            governance_policy = {
                "threshold": approval_threshold,
                "approver_dids": controllers,
            }
        wallet = self.wallet_service.create_wallet(
            owner_did=owner_did,
            controller_dids=list(controller_dids) if controller_dids is not None else None,
            governance_policy=governance_policy,
        )
        self._persist_wallet_if_configured(wallet.wallet_id)
        return wallet


    def get_wallet(self, wallet_id: str):
        return self.wallet_service.get_wallet(wallet_id)


    def add_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        controller_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.add_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            controller_secret=controller_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def remove_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.remove_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def add_device(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        device_did: str,
        device_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.add_device(
            wallet_id,
            actor_did=actor_did,
            device_did=device_did,
            device_secret=device_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def revoke_device(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        device_did: str,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.revoke_device(
            wallet_id,
            actor_did=actor_did,
            device_did=device_did,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def set_recovery_policy(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        contact_dids: Sequence[str],
        threshold: int = 1,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.set_recovery_policy(
            wallet_id,
            actor_did=actor_did,
            contact_dids=list(contact_dids),
            threshold=threshold,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def recover_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        controller_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.recover_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            controller_secret=controller_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet


    def add_location(self, wallet_id: str, *, actor_did: str, lat: float, lon: float):
        record = self.wallet_service.add_location(wallet_id, actor_did=actor_did, lat=lat, lon=lon)
        self._persist_wallet_if_configured(wallet_id)
        return record


