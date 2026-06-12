"""Repo-root compatibility surface for optional ``ipfs_accelerate_py`` imports."""

from __future__ import annotations

from . import hf_space_inference, llm_router

from .hf_space_inference import (
	BatchProcessor,
	BatchState,
	EndpointContract,
	HFBucketBackend,
	HFSpaceClient,
	LocalFileSystemBackend,
	OutputBackend,
	SpaceRuntimeInfo,
)

__all__ = [
	# Modules
	"llm_router",
	"hf_space_inference",
	# Generic HF Space inference provider
	"HFSpaceClient",
	"OutputBackend",
	"LocalFileSystemBackend",
	"HFBucketBackend",
	"BatchProcessor",
	"BatchState",
	"EndpointContract",
	"SpaceRuntimeInfo",
]
