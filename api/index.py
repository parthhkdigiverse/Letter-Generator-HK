import os
import sys
import traceback
import logging
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Initial Prompts ---
LETTER_PROMPTS = {
    "offer": "You are an HR Specialist. Draft a professional Offer Letter. Focus on CTC, joining date, and designation.",
    "appointment": "You are a Corporate Legal Officer. Draft a formal Appointment Letter. Focus on terms, conditions, and company policies.",
    "relieving": "You are an Admin Manager. Draft a Relieving Letter. Focus on the last working day and successful handover."
}

# --- Lazy Database Helper ---
_prompts_collection = None

async def get_collection():
    global _prompts_collection
    if _prompts_collection is not None:
        return _prompts_collection
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        uri = os.getenv("MONGO_URI")
        if not uri:
            logger.error("MONGO_URI environment variable is missing!")
            return None
        
        client = AsyncIOMotorClient(uri)
        db = client.letter_generator_db
        _prompts_collection = db.prompts
        logger.info("MongoDB collection initialized successfully.")
        return _prompts_collection
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        traceback.print_exc()
        return None

async def get_all_prompts():
    coll = await get_collection()
    if coll is None: return []
    prompts = []
    async for prompt in coll.find():
        prompts.append({
            "letter_type": prompt["letter_type"],
            "prompt_text": prompt["prompt_text"]
        })
    return prompts

async def get_prompt_by_type(letter_type: str):
    coll = await get_collection()
    if coll is None: return None
    return await coll.find_one({"letter_type": letter_type})

async def add_or_update_prompt(letter_type: str, prompt_text: str):
    coll = await get_collection()
    if coll is None:
        raise Exception("Database connection failed. Please check your MONGO_URI in Vercel settings.")
    await coll.update_one(
        {"letter_type": letter_type},
        {"$set": {"prompt_text": prompt_text}},
        upsert=True
    )

async def delete_prompt(letter_type: str):
    coll = await get_collection()
    if coll is None: return
    await coll.delete_one({"letter_type": letter_type})

async def seed_initial_prompts(initial_prompts: dict):
    coll = await get_collection()
    if coll is None: return
    count = await coll.count_documents({})
    if count == 0:
        for letter_type, prompt_text in initial_prompts.items():
            await add_or_update_prompt(letter_type, prompt_text)
        logger.info("Database seeded with initial prompts.")

# --- FastAPI App ---
app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    traceback.print_exc()
    return {
        "error": "Internal Server Error",
        "detail": str(exc),
        "traceback": traceback.format_exc()
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes (Explicit /api prefix for Vercel) ---

@app.get("/api/health")
async def health():
    coll = await get_collection()
    return {
        "status": "online",
        "mongo_connected": coll is not None,
        "has_mongo_uri": os.getenv("MONGO_URI") is not None,
        "env_keys": list(os.environ.keys())[:5] # Diagnostic: show first 5 keys
    }

@app.get("/api")
async def root():
    return {"message": "AI Letter Generator API is running on Vercel"}

@app.get("/api/prompts")
async def list_prompts_route():
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

@app.post("/api/prompts")
async def save_prompt_route(data: PromptUpdate):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await add_or_update_prompt(data.letter_type, data.prompt_text)
    return {"message": f"Prompt for '{data.letter_type}' saved."}

@app.delete("/api/prompts/{letter_type}")
async def remove_prompt_route(letter_type: str, password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    await delete_prompt(letter_type)
    return {"message": f"Prompt for '{letter_type}' deleted."}

class LetterRequest(BaseModel):
    letter_type: str
    description: str

@app.post("/api/generate")
async def generate_letter_route(request: LetterRequest):
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY environment variable is not set."}
    
    genai.configure(api_key=api_key)
    api_model = genai.GenerativeModel("gemini-2.5-flash") # Use stable model name
        
    prompt_data = await get_prompt_by_type(request.letter_type)
    system_role = prompt_data["prompt_text"] if prompt_data else "You are a professional business writer."
    
    try:
        prompt = f"System: {system_role}\nUser: Create content based on these details: {request.description}"
        response = api_model.generate_content(prompt)
        return {"content": response.text}
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return {"error": str(e)}