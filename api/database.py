import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

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
        raise Exception("Database not connected. Check MONGO_URI.")
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
    # Check if DB is already seeded
    count = await prompts_collection.count_documents({})
    if count == 0:
        for letter_type, prompt_text in initial_prompts.items():
            await add_or_update_prompt(letter_type, prompt_text)
        print("Database seeded with initial prompts.")
