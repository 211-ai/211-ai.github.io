"""Domain service mixins for WalletInterfaceService."""

from .hmis_service import HmisDomainServiceMixin

try:
    from .interaction_service import InteractionDomainServiceMixin
    from .record_service import RecordDomainServiceMixin
    from .wallet_service import WalletDomainServiceMixin
except ImportError as _err:

    class _MissingOptionalMixin:  # type: ignore[no-redef]
        """Placeholder raised when optional ipfs_datasets_py dep is absent."""

        def __init_subclass__(cls, **kwargs: object) -> None:
            raise ImportError(
                f"Cannot use {cls.__name__}: ipfs_datasets_py is required. "
                "Install it with: pip install -e '.[wallet]'"
            ) from None

    InteractionDomainServiceMixin = _MissingOptionalMixin  # type: ignore[misc,assignment]
    RecordDomainServiceMixin = _MissingOptionalMixin  # type: ignore[misc,assignment]
    WalletDomainServiceMixin = _MissingOptionalMixin  # type: ignore[misc,assignment]

__all__ = [
    "HmisDomainServiceMixin",
    "InteractionDomainServiceMixin",
    "RecordDomainServiceMixin",
    "WalletDomainServiceMixin",
]
