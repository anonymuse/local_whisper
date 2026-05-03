# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**local_whisper (OpenDictate)** is an open-source, self-hosted speech-to-text platform powered by ASR + LLM post-processing. It brings the dictation quality of Claude/ChatGPT apps to anyone who can self-host, with a path to a cloud-hosted SaaS offering.

## How It Works

Two-layer pipeline:
1. **ASR layer** — Faster-Whisper (CTranslate2, INT8 quantization, Whisper Large-v3-Turbo) transcribes audio to raw text
2. **LLM layer** — Language model cleans, punctuates, and corrects the transcript (default: Ollama/gemma4:e4b; optional: Claude Haiku or OpenAI with user-supplied key)

This two-layer approach is why AI app dictation is dramatically better than Apple's built-in speech recognition.

## Deployment Modes

| Mode | Description | Scope |
|---|---|---|
| **1 — Self-Hosted** | iPhone/Windows → home lab (Unraid/Docker/RTX GPU) → Faster-Whisper + LLM → clean text. Access via Tailscale. | MVP |
| **2 — Cloud SaaS** | Same backend code deployed to cloud; users pay a low monthly subscription. OpenDictate operates shared infrastructure. | V2 |
| **3 — On-Device iOS** | WhisperKit (Neural Engine) + small edge LLM (phi-3-mini or similar). Audio never leaves the iPhone. Less accurate, works offline. | Future POC |

## iOS App Architecture

A single `transcribe()` abstraction routes to whichever mode is active. The app never calls ASR or LLM directly — always through this abstraction layer. This enables Mode 1/2/3 switching without rewriting the app.

## Tech Stack

| Layer | Choice |
|---|---|
| ASR | Faster-Whisper, Whisper Large-v3-Turbo (CTranslate2, INT8) |
| LLM post-processing | Ollama/gemma4:e4b (default); Claude Haiku or OpenAI (user-supplied API key) |
| Backend API | Python + FastAPI |
| Packaging | Docker Compose (Unraid-style) |
| iOS client | SwiftUI + custom keyboard extension (system-wide dictation) |
| Windows client | Tauri with global hotkey |
| Networking | Tailscale (Mode 1), standard HTTPS (Mode 2) |

## Development Phases

1. **Backend Core** — FastAPI + Faster-Whisper Docker container
2. **LLM Post-Processing** — chain Whisper output into Claude Haiku
3. **iOS App** — SwiftUI + keyboard extension (Mode 1 client)
4. **Windows App** — Tauri with global hotkey
5. **Unraid Packaging** — Docker Compose + community app template
6. **Cloud Migration** — Mode 2 SaaS deployment
7. **On-Device POC** — WhisperKit + edge LLM (Mode 3)

## Development Approach

- Owner is a technology executive and engineer learning how these systems are built from the ground up
- Goals: understand LLMs, agentic coding workflows, and how to build resilient, efficient, and secure production systems
- Always use plan mode before coding sessions
- One phase at a time, fully explained and documented
- Claude Code is primary development tool
- Every architectural decision made with security, efficiency, and cloud-portability in mind

## Home Lab Architecture

### Hardware
- Windows PC: RTX 5080 FE — runs Ollama as a Windows service (port 11434)
- Unraid server: runs Docker containers — FastAPI gateway, Faster-Whisper
- Proxmox server: future staging, monitoring, mirrors cloud infrastructure

### Service Layout
- FastAPI gateway (Unraid Docker, port 8000) — single entry point for all clients
- Faster-Whisper (same container or sidecar) — GPU inference via Docker passthrough
- LLM post-processor — routes to Ollama local, Windows Ollama, or cloud API
- Ollama — preferred on Unraid Docker; fallback to Windows Ollama over LAN

### LLM Provider Config
```
LLM_PROVIDER=ollama      (default — Unraid or Windows)
LLM_PROVIDER=anthropic   (user brings own API key)
LLM_PROVIDER=openai      (user brings own API key)
OLLAMA_BASE_URL=http://[windows-ip]:11434
OLLAMA_MODEL=gemma4:e4b
```

### Networking
- All clients connect via Tailscale (home lab) or HTTPS (cloud)
- No direct client-to-model connections — everything routes through FastAPI gateway
- Proxmox mirrors cloud topology for local testing

## Ollama Setup (Windows)
- Install Ollama for Windows from ollama.com (current: Ollama 0.22.1)
- Run as a Windows service so it starts on boot
- Pull model: `ollama pull gemma4:e4b` (current default model)
- Expose on LAN so Unraid Docker can reach it

## Inspiration

- **WhisperFlow** — UX and architecture reference
- **Plex, Immich** — deployment model reference
