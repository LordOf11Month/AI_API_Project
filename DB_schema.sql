CREATE TYPE provider AS ENUM ('google', 'openai', 'anthropic', 'deepseek');
CREATE TYPE role AS ENUM ('user', 'assistant', 'system', 'tool');

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_templates (
    name VARCHAR(255) PRIMARY KEY,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version SMALLINT DEFAULT 1,
    tenant_fields JSONB DEFAULT NULL
);


CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    index INT,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    role role NOT NULL,
    content TEXT NOT NULL,

    PRIMARY KEY (index, chat_id)
);


CREATE TABLE requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    
    --MODEL
    model_name TEXT,
    model_provider provider,
    is_client_api BOOLEAN DEFAULT FALSE,
    --TOKENS
    input_tokens INT,
    output_tokens INT,
    reasoning_tokens INT,
    --STATUS
    status BOOLEAN, -- True if success, False if error
    error_message TEXT DEFAULT NULL,
    latency FLOAT,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE API_KEYS (
    api_key UUID PRIMARY KEY NOT null,
    client_id UUID REFERENCES clients(id),
    provider provider
);

-- Indexes
CREATE INDEX idx_messages_chat_id ON messages(chat_id);

