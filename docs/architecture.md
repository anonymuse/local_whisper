# OpenDictate Architecture

## Overview

OpenDictate is a self-hosted speech-to-text platform that chains a fast ASR model with an LLM post-processor to deliver dictation quality comparable to commercial AI apps. A single `transcribe()` abstraction in each client routes to whichever deployment mode is active — the app never calls ASR or LLM directly.

## Two-Layer Pipeline

```
Audio → [Faster-Whisper ASR] → raw text → [LLM Post-Processor] → cleaned transcript
```

1. **ASR layer** — Faster-Whisper (CTranslate2, INT8, Large-v3-Turbo) converts audio to raw text. Fast, accurate, runs locally on GPU.
2. **LLM layer** — Post-processor fixes punctuation, removes filler words, corrects proper nouns, adds paragraph breaks, and lightly improves clarity. Preserves the speaker's voice.

This two-layer approach is why commercial AI dictation apps (Claude, ChatGPT) produce dramatically better output than platform speech recognition (Apple, Windows). OpenDictate brings that quality to self-hosters.

---

## Three Deployment Tiers

### Mode 1 — Self-Hosted (MVP)

Clients connect via Tailscale to a home lab running FastAPI + Faster-Whisper on Unraid Docker, with LLM post-processing routed to a local Ollama instance (Windows PC) or a user-supplied cloud API key.

**Target user:** Developer/hobbyist with a home server and a GPU machine.  
**Cost:** Zero API costs with Ollama. Optional cloud API for higher quality.  
**Privacy:** All audio processed locally. Never touches a cloud inference provider unless the user explicitly configures one.

### Mode 2 — Cloud SaaS (V2)

Same Docker images deployed to cloud infrastructure. Users pay a monthly subscription; OpenDictate operates shared GPU/LLM infrastructure. Clients connect via standard HTTPS — no Tailscale required.

**Target user:** Anyone who wants the quality without self-hosting.  
**Cost:** Subscription fee covers shared inference infrastructure.  
**Privacy:** Audio is processed in OpenDictate's cloud. Standard privacy policy applies.

### Mode 3 — On-Device iOS (Future POC)

WhisperKit (Apple Neural Engine) + small edge LLM (phi-3-mini or similar) running entirely on-device. No network required. Audio never leaves the iPhone.

**Target user:** Privacy-first users, travelers, users in poor-connectivity environments.  
**Cost:** Zero, everything runs on-device.  
**Tradeoff:** Less accurate than Large-v3-Turbo; slower LLM post-processing on mobile silicon.

---

## Home Lab Architecture

### Hardware

| Machine | Role |
|---|---|
| Windows PC (RTX 5080 FE) | Ollama inference host — runs as a Windows service on port 11434 |
| Unraid server | Docker host — FastAPI gateway and Faster-Whisper container |
| Proxmox server | Staging, monitoring, mirrors cloud topology for local testing |

### Service Layout

```
Clients → Tailscale → [Unraid: FastAPI :8000 → Faster-Whisper]
                                         ↓
                         LLM Post-Processor
                         ├── Ollama :11434 (Windows PC, LAN) ← default
                         ├── Anthropic API (user key)
                         └── OpenAI API (user key)
```

**FastAPI Gateway** (`backend/app/main.py`) is the single entry point. It:
- Validates audio format (WAV, m4a, AAC) and duration
- Writes audio to a temp file, calls the transcriber, deletes the temp file
- Passes raw transcript to the LLM post-processor
- Returns `{transcript, raw, duration_seconds}` as JSON

**Faster-Whisper** (`backend/app/transcriber.py`):
- Model loaded once at startup via FastAPI lifespan context manager
- Runs in a thread pool (`asyncio.run_in_executor`) to avoid blocking the async event loop
- ffmpeg handles m4a/AAC → WAV conversion server-side before inference
- Model weights cached in a named Docker volume — survives container rebuilds

**LLM Post-Processor** (`backend/app/postprocessor.py`):
- Routes to the configured provider via `LLM_PROVIDER` env var
- Uses prompt caching on the static system prompt for cost efficiency (Anthropic provider)
- All five cleanup behaviors: punctuation, filler words, proper nouns, paragraph breaks, clarity

---

## LLM Provider Routing

The `LLM_PROVIDER` environment variable controls which backend the post-processor calls. This can be changed at runtime by updating `.env` and restarting the container.

| `LLM_PROVIDER` | Model | Config Required |
|---|---|---|
| `ollama` (default) | `gemma4:e4b` via Ollama 0.22.1 | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| `anthropic` | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| `openai` | configurable | `OPENAI_API_KEY`, `OPENAI_MODEL` |

Ollama is the default because it requires no API key and runs at zero marginal cost on the user's existing GPU hardware.

---

## Networking

**Mode 1** uses Tailscale as the network perimeter. Tailscale provides encrypted mesh networking between the iPhone, Windows PC, and Unraid server without port forwarding or a public IP. No app-level authentication is implemented in the MVP — Tailscale ACLs are the security boundary.

**Mode 2** uses standard HTTPS. Authentication and rate limiting are handled at the application/infrastructure layer.

No client connects directly to Faster-Whisper or Ollama. All traffic routes through the FastAPI gateway.

---

## Technology Decisions

### Faster-Whisper over original Whisper
CTranslate2 runtime with INT8 quantization delivers 4–8x faster inference with minimal quality loss. Large-v3-Turbo is the best quality/speed tradeoff in the Whisper family as of 2025.

### Ollama as default LLM provider
Self-hosters can run the full stack with zero ongoing API costs. gemma4:e4b on an RTX 5080 is fast enough for real-time post-processing. Cloud options are available for users who prefer higher quality or lack local GPU capacity.

### Async Python / FastAPI
FastAPI's async handlers keep the event loop free during long-running audio uploads. Whisper inference runs in a thread pool executor so it doesn't block the loop. Pydantic v2 settings provide fail-fast env var validation at startup.

### Docker named volume for model cache
Faster-Whisper downloads Large-v3-Turbo (~1.5 GB) on first run. A named volume persists the cache across container rebuilds, avoiding repeated downloads during development and upgrades.

### Tailscale over self-managed VPN
Zero configuration, no port forwarding, no exposed public IP. Encrypted by default. No app-level auth to implement for MVP. Scales to Mode 2 by simply replacing it with HTTPS.

### Single-container MVP
FastAPI and Faster-Whisper share one container for simplicity. The service layout supports splitting them into separate containers (sidecar pattern) when scale or isolation requires it, without changing the API contract.

### Synchronous HTTP response
Audio transcription completes in the HTTP response — no job queue, no polling. Acceptable for MVP because max audio duration is configurable (default 300s) and the target is real-time dictation, not batch processing.

---

## Configuration Reference

```
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
MAX_AUDIO_DURATION_SECONDS=300

LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://[windows-ip]:11434
OLLAMA_MODEL=gemma4:e4b

# Optional — only needed for cloud providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```
