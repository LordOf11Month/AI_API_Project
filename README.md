# 🧠 AI API Center – Unified Agent Platform

> A modular, extensible backend platform for configuring, deploying, and managing AI agents with model selection, custom RAG, tool integrations, and fine-grained parameter control.

## 🌐 Overview

AI API Center is a unified backend service for handling AI model interactions in enterprise environments. It abstracts multiple LLM APIs (OpenAI, DeepSeek, Gemini, etc.) into a single, configurable interface.

---

🔑 Key Features

    ⚡ Multi-Model Routing
    Dynamically routes user prompts to the selected LLM backend (e.g., OpenAI, Anthropic, Google Gemini) via clean abstraction layers.

    📡 Streaming Output Support
    Low-latency, token-by-token streaming via SSE (Server-Sent Events) for real-time UI response in chat apps.

    🧾 Logging Layer
    Full prompt-response capture including metadata (timestamp, model, API key owner, etc.) for observability and auditing.

    🛡️ API Key Authentication
    Clients authenticate with individual API keys. Unauthorized requests are blocked automatically.

    🧠 System Prompt Control
    Configure per-session system prompts to steer chatbot behavior. This enables contextually aware agents with domain-specific tone and instruction logic.

🧱 System Architecture

        ┌─────────────────────────────┐
        │        Client App           │
        │    (e.g., Hotel Chatbot)    │
        └────────────┬────────────────┘
                     │ REST API (w/ streaming)
                     ▼
      ┌─────────────────────────────────────┐
      │          Controller Layer           │
      │ - Auth (API Key)                    │
      │ - Stream handling (SSE)             │
      └────────────────┬────────────────────┘
                       ▼
      ┌─────────────────────────────────────┐
      │         Model Router Layer          │
      │ - Dispatch to LLM provider          │
      │ - Load-balancing, failover ready    │
      └────┬────────────┬────────────┬──────┘
           ▼            ▼            ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ GPTHandler │ │ ClaudeHandler │ │ GeminiHandler │
   └────┬───────┘ └────┬────────┘ └────┬────────┘
        ▼              ▼               ▼
   ┌──────────┐   ┌────────────┐   ┌────────────┐
   │ OpenAI   │   │ Anthropic  │   │ Google AI  │
   │ API      │   │ API        │   │ API        │
   └──────────┘   └────────────┘   └────────────┘

🏗️ Project Structure

ai-api-center/
├── app/                     # Main FastAPI app
│   ├── routers/             # API routes
│   ├── handlers/            # Claude, GPT, Gemini integration
│   ├── auth/                # API key auth middleware
│   ├── core/                # Model router, system prompt logic
│   ├── logging/             # Central logging utilities
│   └── config/              # Provider keys, system settings
├── tests/                   # Unit & integration tests
├── requirements.txt         # Python deps
└── README.md

## 🛠️ Tech Stack

| Component     | Technology                                      |
|---------------|--------------------------------------------------|
| **Backend**   | Python (FastAPI or Starlette)                   |
| **Auth**      | JWT (PyJWT), OAuth-ready                        |
| **LLM APIs**  | OpenAI, DeepSeek, Gemini, Claude, etc.          |
| **Logging DB**| PostgreSQL / SQLite                             |

## 👥 Contributors

- **Mehmet Can Özen** - Contributor 👥