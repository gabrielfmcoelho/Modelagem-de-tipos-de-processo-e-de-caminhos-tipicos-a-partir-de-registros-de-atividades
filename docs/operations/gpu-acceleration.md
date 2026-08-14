# GPU Acceleration

Two heavy ML stages benefit from GPU acceleration:

- `embed` — only its **local sentence-transformers fallback** (default model
  `BAAI/bge-m3`, 1024-d, ~568M params); the default Mandu `/v1/embeddings`
  backend costs nothing locally. Force the local path with
  `--flag embedder=local`.
- `ner-extract` — GLiNER2 (default model `fastino/gliner2-base-v1`)

Both auto-detect the best available device on load via `pipeline.devices`.

## Status

**Implemented.** Code paths:

- `pipeline/core/devices.py` — `select_device()`, `select_dtype()`, `autocast_for()`
- `pipeline/model/embedding.py` — `SentenceTransformerEmbedder._load()` passes
  the detected device to the constructor; `embed_batch()` wraps `encode()`
  in `autocast_for(device)` for bf16/fp16 throughput on CUDA/XPU
- `pipeline/stages/ner_extract.py` — loads with
  `GLiNER2.from_pretrained(model, map_location=device)`, checks the model's
  parameters actually landed on the device, and falls back to `.to(device)`
  (then CPU) if not
- `pipeline/tests/test_devices.py` — unit tests with mocked CUDA/XPU/MPS
  availability

Install paths:

- CPU (default): `pip install -r requirements.txt`
- CUDA: `pip install -r requirements.txt && pip install -r requirements-gpu.txt`
  (also pulls `torch-geometric` for `gcn-distill`)
- Container: `docker build -f Dockerfile.gpu -t ai-pipeline-neo4j:gpu .`

## Hardware support matrix

| GPU | Status | Path |
| --- | --- | --- |
| NVIDIA (CUDA, 8+ GB VRAM) | **recommended** | `torch` with `cu121` wheels, native `device="cuda"` |
| NVIDIA (CUDA, <8 GB VRAM) | works with bf16 | force `bf16` autocast + smaller batch |
| AMD ROCm | should work | `torch` with ROCm wheels; `device="cuda"` (PyTorch lies about the name) |
| Intel Arc (XPU) | **not recommended** | requires `intel-extension-for-pytorch`; GLiNER2 not natively supported on XPU |
| Apple Silicon (MPS) | works for embeddings | `device="mps"`, but no GLiNER2 MPS path |
| CPU | always works | current default |

## How it works

### `pipeline/core/devices.py`

Three callables:

- `select_device(preference=None)` — resolves to `"cuda" | "xpu" | "mps" | "cpu"`.
  Honors explicit arg > `PIPELINE_DEVICE` env > auto-detect (CUDA → XPU →
  MPS → CPU). Falls back silently to CPU with a WARNING log if the requested
  device isn't available.
- `select_dtype(preference=None)` — returns a `torch.dtype` from
  `PIPELINE_DTYPE` (`bf16` default, plus aliases like `bfloat16`, `half`,
  `full`).
- `autocast_for(device, dtype_preference=None)` — context manager. Yields a
  no-op on CPU/MPS or when `PIPELINE_DTYPE=fp32`; yields
  `torch.autocast(device_type=..., dtype=...)` on CUDA/XPU otherwise.

`device_summary()` produces a one-line startup log entry — useful for
verifying the pipeline picked up the right device.

### Embedding stage (`pipeline/model/embedding.py`)

`SentenceTransformerEmbedder._load()` calls `select_device()` and forwards
the result to `SentenceTransformer(..., device=...)`. `embed_batch()` wraps
the `encode()` call in `autocast_for(self._device)` and respects
`PIPELINE_EMBED_BATCH_SIZE` (default 64).

### NER stage (`pipeline/stages/ner_extract.py`)

`GLiNER2.from_pretrained(args.model, map_location=device)` is tried first.
The stage then inspects `next(extractor.parameters()).device`; if the model
didn't land on the requested device it tries `.to(device)`, and on failure
logs and drops back to CPU rather than crashing.

### Install paths

- `requirements.txt` — CPU defaults (works everywhere; torch comes in as a
  transitive dep of sentence-transformers / gliner2)
- `requirements-gpu.txt` — adds the PyTorch `cu121` index, pins
  `torch>=2.3,<3.0`, and adds `torch-geometric>=2.5` for `gcn-distill`.
  Install on top of `requirements.txt`.
- `Dockerfile.gpu` — `nvidia/cuda:12.1.1-runtime-ubuntu22.04` base, Python
  3.11, both requirement files installed in sequence.

## Operational lessons (full-corpus NER runs, 8 GB GPU)

Hard-won facts from running `ner-extract` over the full corpus on an 8 GB
NVIDIA card:

- **At most 2-3 concurrent GPU workers.** `ner-extract` shards the corpus
  for parallel workers (`--shard K/N`), each loading its own GLiNER2 copy.
  A 5-worker run caused CUDA OOM on **all** chunks of 1,928 long documents
  — the workers survived but every long doc came back empty. 2-3 workers
  fit comfortably.
- **`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` eliminated the OOMs
  entirely on the retry.** Long documents are split into ~1800-char chunks
  of varying length; the default CUDA caching allocator fragments under
  those variable-sized allocations. Set it on every GPU NER run:

  ```bash
  # one of three parallel workers (0/3, 1/3, 2/3 in separate terminals)
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    python -m pipeline run ner-extract --no-deps --force-stage ner-extract \
      --flag shard=0/3
  ```

- **Sharded, idempotent retries.** `--flag shard=K/N` processes only shard
  K of N (deterministic split of the corpus), and skip-existing is the
  default through the runner — a doc with a JSON already in `ner_results/`
  is skipped — so a crashed or OOM'd worker can simply be relaunched with
  the same command. (`--force-stage ner-extract` busts the runner
  checkpoint; the per-doc skip still protects finished work.)

## Hardware-specific notes

### NVIDIA RTX 2000 Ada (8 GB VRAM)

This is Ada Lovelace architecture — bf16 throughput is excellent, dedicated
Tensor cores. With `BAAI/bge-m3` (1024-d, ~568M params):

- fp32 resident: ~2.3 GB → batch 32-64 comfortable
- bf16 resident: ~1.2 GB → batch 64-128 comfortable
- Activations for batch 64 × 8192 tokens stay well under 4 GB

Recommended settings for this card:

```bash
PIPELINE_DEVICE=cuda
PIPELINE_DTYPE=bf16
PIPELINE_EMBED_BATCH_SIZE=64
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

Expected speedup: 5-10× over CPU for `ner-extract`, 10-20× for local
`embed`.

### Intel Arc (XPU) — why we skip it

Two real problems:

1. **GLiNER2 doesn't have a native XPU path.** It would need OpenVINO
   conversion or IPEX (Intel Extension for PyTorch) patching of the
   underlying HF Transformer. Non-trivial.
2. **Dual-GPU dispatch isn't free.** PyTorch doesn't auto-shard work across
   CUDA + XPU. To use both you'd manually partition: one process pinned to
   CUDA for embedding, another to XPU for NER. Ops overhead exceeds the
   gain at this scale.

**Recommendation**: on a laptop with both an NVIDIA dGPU and an Intel Arc
iGPU, use the NVIDIA dGPU for the pipeline and leave the Arc for display.
If you genuinely need Arc utilization, the cleanest path is to run an
OpenVINO-converted `bge-m3` as a separate inference service — a bigger
project than this acceleration work.

### Lower-VRAM cards (4-6 GB)

- Force `bf16` (halves activation memory)
- Drop batch to 16-32
- Disable `torch.compile` (its memory overhead can push you OOM)
- Run a single NER worker (no `--shard` parallelism)

### Apple Silicon (MPS)

- `device="mps"` works for sentence-transformers
- GLiNER2 falls back to CPU on MPS — not a problem, just no acceleration
  there
- bf16 on MPS is limited; use fp32

## Validation checklist (per environment)

After installing GPU torch and pointing `PIPELINE_DEVICE` at your target:

```bash
# 1. Confirm torch sees the device
python -c "from pipeline.devices import device_summary; print(device_summary())"
# Expect: device=cuda name='NVIDIA RTX 2000 Ada Generation' count=1 dtype=bf16

# 2. Validate embeddings stay within ~0.5% of CPU baseline on a fixed corpus.
# --emit-dir implies json-emit mode (no graph writes); rows land in
# templates/load_documento_embedding.ndjson under the emit dir.
PIPELINE_DEVICE=cpu  python -m pipeline run embed --no-deps --force-stage embed \
    --limit 50 --flag embedder=local --emit-dir /tmp/emb-cpu
PIPELINE_DEVICE=cuda python -m pipeline run embed --no-deps --force-stage embed \
    --limit 50 --flag embedder=local --emit-dir /tmp/emb-gpu
# Tolerance: cosine similarity between paired vectors should be ≥ 0.995

# 3. Validate NER entity recall on a held-out set (separate output dirs so
# the per-doc skip-existing check doesn't hide the second run)
PIPELINE_DEVICE=cpu  python -m pipeline run ner-extract --no-deps --force-stage ner-extract \
    --limit 20 --flag output=/tmp/ner-cpu
PIPELINE_DEVICE=cuda python -m pipeline run ner-extract --no-deps --force-stage ner-extract \
    --limit 20 --flag output=/tmp/ner-gpu
# Compare entity counts and spans — bf16 inference can shift confidence
# scores by ±0.02 but should not change entity identity at typical thresholds.
```

## Possible follow-ups (not yet implemented)

- **`torch.compile`** on the bge-m3 inner module
  (`mode="reduce-overhead"`) for ~1.2–1.5× extra throughput on long batch
  runs. Skip for short CLI runs (cold compile takes 30–60 s). Combined
  with autocast it occasionally produces NaN; validate cosine after
  enabling.
- **`torch.cuda.empty_cache()` between large model loads** if a single
  process ever runs `embed` and `ner-extract` back-to-back (today they're
  separate CLI invocations, so VRAM is freed naturally).
- **Multi-GPU dispatch** — not relevant for the RTX 2000 Ada (single GPU)
  but possible later via `device_map="auto"` on HF Transformers if the
  fleet grows.

## Pitfalls to avoid

- **Don't stack autocast + `.half()` + `torch.compile`** without testing.
  They interact subtly and can produce NaN/inf in normalizers (sentence
  embeddings rely on L2 norm being stable).
- **Don't assume `torch.cuda.is_available()` means GPU.** On Docker without
  `--gpus all` (or compose's `deploy.resources.reservations.devices`), the
  CUDA libs may be present but no devices show up. `device_summary()`
  prints `count=N` so you can confirm visibility on startup.
- **Don't run the CPU image expecting GPU.** The default `Dockerfile`
  installs the CPU torch wheel. To use CUDA, build with
  `docker build -f Dockerfile.gpu` and run with `--gpus all`.
- **Don't over-parallelize NER shards.** See the operational lessons above
  — 8 GB tolerates 2-3 workers, and `expandable_segments:True` is the
  difference between an OOM-riddled run and a clean one.
