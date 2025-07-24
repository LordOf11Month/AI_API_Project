burası documana eklemek için notlarım


1.yeni bir provider eklendiğinde
    1.handlerini yaz(handler klasörüne tabiki)
    2.dispatcher.py dosyasındaki arrayi güncelle
      # A mapping of provider names to their handler classes-----------------
        HANDLERS = {
            "google": GoogleHandler,
            "openai": OpenAIHandler,                                                THİS GUY
            "anthropic": AnthropicHandler,
            "deepseek": DeepseekHandler,
        }

    #------------------------------------------------------------------------

    3.databaseden api key tablosunun proiver setini güncelle
            CREATE TABLE API_KEYS (
                api_key UUID PRIMARY KEY NOT null,
                client_id UUID REFERENCES clients(id),
                Provider VARCHAR(50) CHECK (Provider IN ('google', 'openai', 'anthropic','deepseek')), <----- this guy
                api_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

i would rather be lord of freanzied flame then entagratiıng DB 😭🙏