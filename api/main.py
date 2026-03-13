import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from database import (
    get_all_prompts, get_prompt_by_type, add_or_update_prompt, 
    delete_prompt, seed_initial_prompts
)
from prompts import LETTER_PROMPTS

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    print("WARNING: GEMINI_API_KEY is not set!")
    model = None

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Seed initial prompts if DB is empty
    await seed_initial_prompts(LETTER_PROMPTS)

@app.get("/")
async def root():
    return {"message": "AI Letter Generator API is running with Gemini and MongoDB"}

# --- Prompt Management Endpoints (Admin Only) ---

ADMIN_PASSWORD = "admin123" # Simple hardcoded password for now

class PromptUpdate(BaseModel):
    letter_type: str
    prompt_text: str
    password: str

@app.get("/prompts")
async def list_prompts():
    return await get_all_prompts()

@app.post("/prompts")
async def save_prompt(data: PromptUpdate):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await add_or_update_prompt(data.letter_type, data.prompt_text)
    return {"message": f"Prompt for '{data.letter_type}' saved."}

@app.delete("/prompts/{letter_type}")
async def remove_prompt(letter_type: str, password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await delete_prompt(letter_type)
    return {"message": f"Prompt for '{letter_type}' deleted."}

# --- Generation Endpoint ---

class LetterRequest(BaseModel):
    letter_type: str
    description: str

@app.post("/generate")
async def generate_letter(request: LetterRequest):
    # Fetch prompt from DB
    prompt_data = await get_prompt_by_type(request.letter_type)
    system_role = prompt_data["prompt_text"] if prompt_data else "You are a professional business writer."
    
    try:
        # Gemini prompt format: combine system role and user request
        prompt = f"System: {system_role}\nUser: Create content based on these details: {request.description}"
        response = model.generate_content(prompt)
        
        return {"content": response.text}
    except Exception as e:
        print(f"Error generating letter: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)