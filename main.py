from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from sentence_transformers import SentenceTransformer, util

app = FastAPI(title="EventAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "users.json"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    interests: Optional[List[str]] = None

def load_users(json_path: str = DATA_FILE) -> List[Dict[str, Any]]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Users file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format in users file")

def save_users(users: List[Dict[str, Any]], json_path: str = DATA_FILE):
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write users file: {str(e)}")

def find_top_3_interest_matches(user_id: str, json_path: str = DATA_FILE, threshold: float = 0.6):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    with open(json_path, "r") as f:
        users = json.load(f)

    target_user = next((u for u in users if u["id"] == user_id), None)
    if not target_user:
        raise ValueError(f"User with ID '{user_id}' not found.")
    
    target_interests = target_user.get("interests", [])
    if not target_interests:
        raise ValueError(f"User '{user_id}' has no interests.")

    target_embeddings = model.encode(target_interests, convert_to_tensor=True)
    matches = []

    for user in users:
        if user["id"] == user_id:
            continue

        other_interests = user.get("interests", [])
        if not other_interests:
            continue

        other_embeddings = model.encode(other_interests, convert_to_tensor=True)
        sim_matrix = util.pytorch_cos_sim(target_embeddings, other_embeddings)
        common_interests = set()

        for i, target_interest in enumerate(target_interests):
            for j, other_interest in enumerate(other_interests):
                if sim_matrix[i][j].item() >= threshold:
                    common_interests.add(other_interest)

        if not common_interests:
            continue

        target_mean = target_embeddings.mean(dim=0)
        other_mean = other_embeddings.mean(dim=0)
        similarity = util.pytorch_cos_sim(target_mean, other_mean).item()

        matches.append({
            "user_id": user["id"],
            "name": user["full_name"],
            "email": user.get("email", "N/A"),
            "job_title": user.get("job_title", "N/A"),
            "company": user.get("company", "N/A"),
            "score": round(similarity * 100, 2),
            "interests": list(common_interests)
        })

    return sorted(matches, key=lambda x: x["score"], reverse=True)[:3]


@app.get("/")
def root():
    return {"message": "🧩 Simple Interest-Based Matchmaker API is running."}


@app.get("/match")
def get_matches():
    try:
        results = find_top_3_interest_matches("user_001")
        return {
            "user_id": "user_001",
            "top_matches": results
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/users", response_model=List[Dict[str, Any]])
def get_all_users():
    try:
        users = load_users()
        return users
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.put("/users/{user_id}")
def update_user(user_id: str, user_update: UserUpdate):
    users = load_users()
    for i, user in enumerate(users):
        if user["id"] == user_id:
            updated_user = {**user, **user_update.dict(exclude_unset=True)}
            users[i] = updated_user
            save_users(users)
            return {"message": "User updated", "user": updated_user}
    raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found.")

@app.get("/user", response_model=Dict[str, Any])
def get_user_001():
    """Return only the user with ID 'user_001'."""
    users = load_users()
    user = next((u for u in users if u["id"] == "user_001"), None)

    if not user:
        raise HTTPException(status_code=404, detail="User 'user_001' not found.")

    return user

