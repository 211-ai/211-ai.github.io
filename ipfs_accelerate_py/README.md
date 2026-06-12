# Generic Hugging Face Space Inference Provider

A reusable, generic Python library for batch processing through Hugging Face Spaces with pluggable output backends and automatic retry/resumability.

## What's New

Extracted from the working IndexTTS Abby TTS implementation, this new `ipfs_accelerate_py` module provides generic abstractions that work with **any** Hugging Face Space, not just IndexTTS.

## Quick Example

```python
from ipfs_accelerate_py import (
    HFSpaceClient,
    BatchProcessor, 
    HFBucketBackend,
)
from pathlib import Path

# Connect to any Hugging Face Space
client = HFSpaceClient("https://my-space.hf.space")

# Verify it's ready
contract = client.probe_contract()
assert contract["available"]

# Output to local or HF bucket (pluggable!)
backend = HFBucketBackend("hf://buckets/my-org/outputs")

# Batch process with automatic retry and checkpointing
processor = BatchProcessor(
    client=client,
    output_backend=backend,
    state_file=Path("state.json"),
    batch_size=8,
    retry_attempts=3,
)

# Process items
items = [{"text": "hello"}, {"text": "world"}]
success, results = processor.process_batch(
    items=items,
    endpoint_fn_index=0,
    output_batch_id="batch-001",
)
```

## Architecture

**Three core abstractions:**

1. **HFSpaceClient**: Interacts with Gradio Spaces
   - Endpoint discovery from Space config
   - Synchronous API calls
   - Contract probing for health checks

2. **OutputBackend**: Pluggable output (interface)
   - `LocalFileSystemBackend`: Write to disk
   - `HFBucketBackend`: Write to HF buckets
   - Implement custom backends for S3, GCS, etc.

3. **BatchProcessor**: Orchestrates batch processing
   - Automatic retry with exponential backoff
   - State checkpointing for resumability
   - Pluggable output backend

**Key design principle:** Generic ≠ specific to IndexTTS. The user (you) provides:
- Space URL
- Endpoint index
- Input/output transformations
- Output destination

The library handles:
- Endpoint calls with retry logic
- State checkpointing for resumability
- Output syncing to any backend
- Exponential backoff

## Files

- `ipfs_accelerate_py/hf_space_inference.py` - Core module (350 lines, fully tested)
- `ipfs_accelerate_py/space_inference_example.py` - Usage examples
- `ipfs_accelerate_py/HF_SPACE_INFERENCE.md` - API documentation
- `ipfs_accelerate_py/MIGRATION_GUIDE.md` - How to refactor existing code
- `tests/test_hf_space_inference.py` - 19 unit tests (all passing)

## Why This Matters

### Before (IndexTTS-specific)
```
scripts/precompute_indextts_responses.py: 600+ lines
├─ Gradio/Space interaction (50 lines)
├─ IndexTTS batch call logic (100 lines, hardcoded)
├─ Retry/backoff (80 lines, generic)
├─ Split salvage (100 lines, generic)
├─ Output syncing (150 lines, generic)
└─ Manifest handling (120 lines, IndexTTS-specific)
```

### After (Generic + adapters)
```
ipfs_accelerate_py/hf_space_inference.py: 350 lines (REUSABLE)
├─ HFSpaceClient (80 lines)
├─ OutputBackend + implementations (120 lines)
├─ BatchProcessor + retry (90 lines)
└─ BatchState + utilities (60 lines)

+ Workflow adapters: 100-200 lines per Space (ONLY Space-specific code)
```

**Result:** 400+ lines of generic code → 350 lines (reusable for ANY Space) + minimal adapters per Space

## Use Cases

- **Audio synthesis** (IndexTTS, TTS models)
- **Image embeddings** (CLIP, ViT)
- **Text generation** (LLMs)
- **Document processing** (OCR, parsing)
- **Any Gradio Space** with batch endpoints

## Supported Output Backends

- **Local filesystem**: `LocalFileSystemBackend`
- **HF buckets**: `HFBucketBackend` (using hf-cli)
- **Custom**: Implement `OutputBackend` interface

## Key Features

✅ **Generic**: Works with any Space, any endpoint, any data format  
✅ **Resumable**: State checkpointing enables crash recovery  
✅ **Retryable**: Exponential backoff for transient failures  
✅ **Pluggable**: Swap output backends without code changes  
✅ **Tested**: 19 unit tests, all passing  
✅ **Production-ready**: Extracted from working Abby TTS pipeline  

## Integration Points

- **For new Spaces**: Use this module directly
- **For existing Abby TTS**: Gradual migration path available (see `MIGRATION_GUIDE.md`)
- **For other projects**: Copy `ipfs_accelerate_py.hf_space_inference` into your repo

## Documentation

See:
- `HF_SPACE_INFERENCE.md` - Full API reference and design philosophy
- `MIGRATION_GUIDE.md` - How to refactor IndexTTS scripts
- `space_inference_example.py` - Working code examples
- `tests/test_hf_space_inference.py` - Test suite showing usage patterns

## Next Steps

1. **Try the examples**: `python -m ipfs_accelerate_py.space_inference_example`
2. **Run tests**: `pytest tests/test_hf_space_inference.py -v`
3. **Read the docs**: Start with `HF_SPACE_INFERENCE.md`
4. **Build your adapter**: Create a workflow class for your Space (100-200 lines)
5. **Integrate**: Import from `ipfs_accelerate_py` and use BatchProcessor

## Contributing

To add support for a new Space:

1. Create a workflow class (inherit from nothing, just use the generic APIs)
2. Implement Space-specific transforms (input/output)
3. Use `HFSpaceClient`, `BatchProcessor`, and an `OutputBackend`
4. Test against your Space
5. Share back!

## License

Same as 211-ai.github.io repo
