import os
import sys
import traceback
from fastapi import FastAPI, HTTPException, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- Initial Prompts (Self-contained) ---
LETTER_PROMPTS = {
    "offer": "You are an HR Specialist. Draft a professional Offer Letter. Focus on CTC, joining date, and designation.",
    "appointment": "You are a Corporate Legal Officer. Draft a formal Appointment Letter. Focus on terms, conditions, and company policies.",
    "relieving": "You are an Admin Manager. Draft a Relieving Letter. Focus on the last working day and successful handover."
}

# --- Database Logic (Self-contained) ---
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("WARNING: MONGO_URI environment variable is not set!")

client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
db = client.letter_generator_db if client else None
prompts_collection = db.prompts if db else None

async def get_all_prompts():
    if prompts_collection is None:
        return []
    prompts = []
    async for prompt in prompts_collection.find():
        prompts.append({
            "letter_type": prompt["letter_type"],
            "prompt_text": prompt["prompt_text"]
        })
    return prompts

async def get_prompt_by_type(letter_type: str):
    if prompts_collection is None:
        return None
    return await prompts_collection.find_one({"letter_type": letter_type})

async def add_or_update_prompt(letter_type: str, prompt_text: str):
    if prompts_collection is None:
        raise Exception("Database not connected. Check MONGO_URI environment variable on Vercel.")
    await prompts_collection.update_one(
        {"letter_type": letter_type},
        {"$set": {"prompt_text": prompt_text}},
        upsert=True
    )

async def delete_prompt(letter_type: str):
    if prompts_collection is None:
        return
    await prompts_collection.delete_one({"letter_type": letter_type})

async def seed_initial_prompts(initial_prompts: dict):
    if prompts_collection is None:
        return
    count = await prompts_collection.count_documents({})
    if count == 0:
        for letter_type, prompt_text in initial_prompts.items():
            await add_or_update_prompt(letter_type, prompt_text)
        print("Database seeded with initial prompts.")

# --- AI Configuration ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    print("WARNING: GEMINI_API_KEY is not set!")
    model = None

# --- FastAPI App ---
app = FastAPI()
router = APIRouter(prefix="/api")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"GLOBAL ERROR: {exc}")
    traceback.print_exc()
    return {"error": "Internal Server Error", "detail": str(exc), "traceback": traceback.format_exc()}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
@router.get("/health")
async def health():
    return {
        "status": "online",
        "mongo_connected": prompts_collection is not None,
        "gemini_connected": model is not None,
        "has_mongo_uri": MONGO_URI is not None,
        "has_gemini_key": api_key is not None
    }

@router.get("/")
async def root():
    return {"message": "AI Letter Generator API is running on Vercel (Consolidated)"}

@router.get("/prompts")
async def list_prompts():
    prompts = await get_all_prompts()
    if not prompts:
         await seed_initial_prompts(LETTER_PROMPTS)
         prompts = await get_all_prompts()
    return prompts

class PromptUpdate(BaseModel):
    letter_type: str
    prompt_text: str
    password: str

ADMIN_PASSWORD = "admin123"

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