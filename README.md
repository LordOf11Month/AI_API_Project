# 🧠 AI API Center – Unified Agent Platform

> A modular, extensible backend platform for interacting with multiple AI providers through a single, unified interface.

## 🌐 Overview

The Unified AI API is a backend service designed to abstract the complexities of various Large Language Model (LLM) providers (like OpenAI, Google, Anthropic, and DeepSeek). It provides a single, consistent API for text generation, conversational chat, and dynamic model routing, making it easy to build and manage AI-powered applications.

---

## 🔑 Key Features

-   **⚡ Multi-Provider Support**: Seamlessly switch between AI providers (OpenAI, Google, Anthropic, DeepSeek) with a single API call.
-   **📡 Streaming Responses**: Real-time, token-by-token streaming for interactive applications using Server-Sent Events (SSE).
-   **💬 Conversational Chat**: Built-in support for stateful conversations with persistent chat history stored in the database.
-   **📝 Prompt Templating**: Create and manage reusable prompt templates with dynamic variable substitution for consistent and controlled AI responses.
-   **🔐 Authentication & Security**: Secure user authentication with JWT, per-client API key management, and password hashing.
-   **📊 Request Logging**: Comprehensive logging of all AI requests, including token counts, latency, and status for analytics and monitoring.

## 🧱 System Architecture

```
        ┌─────────────────────────┐
        │       Client App        │
        └────────────┬────────────┘
                     │ REST API (/api/generate, /api/chat)
                     ▼
      ┌─────────────────────────────────┐
      │         FastAPI Server          │
      │   - Authentication Middleware   │
      │   - Request/Response Models     │
      └────────────┬────────────────────┘
                   │
                   ▼
      ┌─────────────────────────────────┐
      │        Request Dispatcher       │
      │   - Route to Provider Handler   │
      │   - Render Prompt Template      │
      │   - Manage API Keys             │
      └────┬────────────┬───────────┬───┘
           ▼            ▼           ▼
   ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
   │ OpenAI     │ │ Google   │ │ Anthropic│ │ DeepSeek   │
   │ Handler    │ │ Handler  │ │ Handler  │ │ Handler    │
   └────┬───────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘
        │              │            │             │
        ▼              ▼            ▼             ▼
   ┌───────────────────────────────────────────────────┐
   │                External AI Providers              │
   └───────────────────────────────────────────────────┘

      ┌─────────────────────────────────┐
      │        Database (PostgreSQL)    │
      │   - Clients & API Keys          │
      │   - Chat History & Messages     │
      │   - Prompt Templates            │
      │   - Request Logs                │
      └─────────────────────────────────┘
```

## 🏗️ Project Structure

```
unified-ai-api/
├── app/                     # Main FastAPI application
│   ├── auth/                # Authentication (JWT, passwords, middleware)
│   ├── DB_connection/       # Database managers (clients, chats, API keys, etc.)
│   ├── handlers/            # Handlers for each AI provider
│   ├── models/              # Pydantic and SQLAlchemy models
│   ├── routers/             # Request dispatcher
│   ├── utils/               # Utility modules (e.g., logger)
│   ├── root_prompt.txt      # Optional root prompt template
│   └── server.py            # FastAPI server entrypoint
├── tests/                   # Unit and integration tests
├── requirements.txt         # Python dependencies
└── README.md
```

## 🛠️ Tech Stack

| Component      | Technology                               |
|----------------|------------------------------------------|
| **Backend**    | Python, FastAPI                          |
| **Database**   | PostgreSQL (with SQLAlchemy)             |
| **Auth**       | JWT (PyJWT), passlib (for hashing)       |
| **LLM APIs**   | OpenAI, Google, Anthropic, DeepSeek      |
| **Templating** | Jinja2                                   |

## 🚀 Getting Started

### 1. Prerequisites

-   Python 3.10+
-   PostgreSQL database

### 2. Setup

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/LordOf11Month/AI_API_Project
    cd unified-ai-api
    ```

2.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**
    Create a `.env` file in the root directory and add the following:
    ```env
    # Database connection
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=your_db_name

    # JWT secret key
    JWT_SECRET_KEY=your-super-secret-key

    # System-wide API keys (optional fallback)
    OPENAI_API_KEY=your-openai-key
    GOOGLE_API_KEY=your-google-key
    ANTHROPIC_API_KEY=your-anthropic-key
    DEEPSEEK_API_KEY=your-deepseek-key

    # Logger configuration
    LOG_DEBUG=true
    ```

### 3. Running the Server

1.  **Start the FastAPI server:**
    ```sh
    uvicorn app.server:app --reload
    ```
2.  **Access the API docs** at `http://127.0.0.1:8000/docs`.

## 👥 Contributors

-   **Ramazan Seçilmiş** - Main Contributor 👑
-   **Mehmet Can Özen** - Contributor 👥