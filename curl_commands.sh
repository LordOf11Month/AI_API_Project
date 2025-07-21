


curl -X 'POST' \
  'http://127.0.0.1:8000/api/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "provider": "google",
    "model": "gemini-1.5-flash-latest",
    "stream": false,
    "userPrompt": "What are the top 3 benefits of using FastAPI?",
    "parameters": {
        "temperature": 0.7
    },
    "clientSystemPrompt": "You are a helpful tech assistant."
}'

curl -N -X 'POST' \
  'http://127.0.0.1:8000/api/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "provider": "google",
    "model": "gemini-1.5-flash-latest",
    "stream": true,
    "userPrompt": "Write a short story about a robot exploring a lush jungle.",
    "parameters": {
        "temperature": 0.8
    }
}'