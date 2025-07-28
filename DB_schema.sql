CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    --client_id UUID REFERENCES clients(id),
    name VARCHAR(255) UNIQUE,
    prompt TEXT NOT NULL,
    --type VARCHAR(50) CHECK (type IN ('chat', 'translate', 'custom')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    version SMALLINT DEFAULT 1
    tenant_fields JSONB DEFAULT NULL
);


CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE requests (
    id UUID PRIMARY KEY,
    chat_id UUID REFERENCES chats(id) ON DELETE SET NULL,
    client_id UUID REFERENCES clients(id),

    --SYSTEM PROMPT 
    prompt_template_id UUID REFERENCES prompt_templates(id),
    system_prompt_tenants JSONB DEFAULT NULL,
    template_version SMALLINT DEFAULT 1,
    
    --MODEL
    model_name TEXT NOT NULL,

    --CONTENT
    request TEXT NOT NULL,
    response TEXT NOT NULL,

    --TOKENS
    input_tokens INT,
    output_tokens INT,

    --STATUS
    status BOOLEAN, -- True if success, False if error
    error_message TEXT DEFAULT NULL,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE API_KEYS (
    api_key UUID PRIMARY KEY NOT null,
    client_id UUID REFERENCES clients(id),
    Provider VARCHAR(50) CHECK (Provider IN ('google', 'openai', 'anthropic','deepseek'))
);

-- Indexes
CREATE INDEX idx_requests_chat_id ON requests(chat_id);
CREATE INDEX idx_requests_created_at ON requests(created_at ASC);
