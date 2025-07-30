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

templateler!!!!!!!!!!!!!! openai system prompt generator
console log zenginleştirme
latency
template seçme url argument olabilir
client api key kullanımı
defualt değerler (model ısı falan)
tools !!
clientta hata döndürme!! teknik değil ama anlamlı?!
log kapatıp açabilme



--ADVENCE----
mvp server
rag


first succesfull sign in 

(.venv) [bne@nazamar AI_API_Project]$ curl -X POST http://localhost:8000/api/signup      -H "Content-Type: application/json"      -d '{
           "email": "example@example.com",
           "password": "yourpassword"
         }'


>>>{"client_id":"0cb4d388-c792-416c-a7de-5118760c0db7","email":"example@example




(.venv) [bne@nazamar AI_API_Project]$ gnup      -H http://localhost:8000/api/signup      -H "Content-Type: application/json"      -d '{
           "email": "a@a.a",
           "password": "Asd123"
         }'




>>>{"client_id":"8984318d-887f-446d-bd67-ad8e810ae922","email":"a@a.a"}

(.venv)[bne@nazamar AI_API_Project]$ curl -X POST http://localhost:8000/api/template \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiIwY2I0ZDM4OC1jNzkyLTQxNmMtYTdkZS01MTE4NzYwYzBkYjciLCJleHAiOjE3NTM3OTM2OTB9.4uC-Auy4Bsqn07rR0Wr0cJZOLoZd72N_IHWaq2zcfU0" \
     -d '{
  "name": "hotel_chatbot",
  "prompt": "You are HotelBot for \"{{ hotel_name }}\", located in {{ location }}. Your role is to assist guests with:\n\n" +
            "- Room availability and booking details\n" +
            "- Check‑in and check‑out procedures\n" +
            "- On‑site amenities information (e.g., {{ amenities }})\n" +
            "- Local recommendations\n\n" +
            "Always respond in a friendly, concise tone.",
  "tenant_fields": [
    "hotel_name",
    "location",
    "amenities"
  ]
}'

>>>{
    "id": "4d2ba984-758d-4d1e-86c0-ab4da337367e",
    "name": "hotel_chatbot",
    "version": 1,
    "tenant_fields": [
        "hotel_name",
        "location",
        "amenities"
    ],
    "created_at": "2025-07-29T11:19:06.051543"
    }


(.venv) [bne@nazamar AI_API_Project]$ curl -X POST http://localhost:8000/api/generate \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiIwY2I0ZDM4OC1jNzkyLTQxNmMtYTdkZS01MTE4NzYwYzBkYjciLCJleHAiOjE3NTM3OTM2OTB9.4uC-Auy4Bsqn07rR0Wr0cJZOLoZd72N_IHWaq2zcfU0" \
     -d '{
           "provider": "google",
           "model": "gemini-1.5-flash-latest",
           "systemPrompt": {
             "template_name": "hotel_chatbot",
             "tenants": {
               "hotel_name": "Grand Hotel",
               "location": "Downtown City",
               "amenities": "Pool, Spa, Restaurant, Gym"
             }
           },
           "userprompt": "What are the available rooms?",
           "parameters": {},
           "stream": false
         }'

>>>{
    "response": {
        "response": "To answer your question accurately, I need more information.  Please tell me which hotel, venue, or building you're interested in.\n"
                }
    }

curl -X POST http://localhost:8000/api/generate \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiIwY2I0ZDM4OC1jNzkyLTQxNmMtYTdkZS01MTE4NzYwYzBkYjciLCJleHAiOjE3NTM3OTM2OTB9.4uC-Auy4Bsqn07rR0Wr0cJZOLoZd72N_IHWaq2zcfU0" \
     -d '{
           "provider": "google",
           "model": "gemini-1.5-flash-latest",
           "systemPrompt": {
             "template_name": "empty_template",
             "tenants": {
               "SystemPrompt": ""
             }
           },
           "userprompt": "this is api test answer with one word apple",
           "parameters": {},
           "stream": false
         }'