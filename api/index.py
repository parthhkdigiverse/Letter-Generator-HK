import os
import sys

# Ensure the 'api' directory is in the path for imports to work on Vercel
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import traceback

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
router = APIRouter(prefix="/api")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"GLOBAL ERROR: {exc}")
    traceback.print_exc()
    return {"error": "Internal Server Error", "detail": str(exc)}

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Seeding (Manual/Lazy) ---
@router.get("/seed")
async def seed_db():
    await seed_initial_prompts(LETTER_PROMPTS)
    return {"message": "Seeding triggered"}

@router.get("/")
async def root():
    return {"message": "AI Letter Generator API is running on Vercel"}

# --- Prompt Management Endpoints ---
ADMIN_PASSWORD = "admin123"

class PromptUpdate(BaseModel):
    letter_type: str
    prompt_text: str
    password: str

@router.get("/prompts")
async def list_prompts():
    # Lazy seed check if prompts are empty (optional, but safe)
    prompts = await get_all_prompts()
    if not prompts:
         await seed_initial_prompts(LETTER_PROMPTS)
         prompts = await get_all_prompts()
    return prompts

@router.post("/prompts")
async def save_prompt(data: PromptUpdate):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await add_or_update_prompt(data.letter_type, data.prompt_text)
    return {"message": f"Prompt for '{data.letter_type}' saved."}

@router.delete("/prompts/{letter_type}")
async def remove_prompt(letter_type: str, password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await delete_prompt(letter_type)
    return {"message": f"Prompt for '{letter_type}' deleted."}

# --- Generation Endpoint ---
class LetterRequest(BaseModel):
    letter_type: str
    description: str

@router.post("/generate")
async def generate_letter(request: LetterRequest):
    if model is None:
        return {"error": "AI model not configured (missing API key)"}
        
    prompt_data = await get_prompt_by_type(request.letter_type)
    system_role = prompt_data["prompt_text"] if prompt_data else "You are a professional business writer."
    
    try:
        prompt = f"System: {system_role}\nUser: Create content based on these details: {request.description}"
        response = model.generate_content(prompt)
        return {"content": response.text}
    except Exception as e:
        print(f"Error generating letter: {e}")
        return {"error": str(e)}

app.include_router(router)