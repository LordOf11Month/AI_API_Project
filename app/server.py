from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()



@app.post("/")
async def root():
    print("its working")
