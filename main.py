import json
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="EventAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

def load_users(json_path: str = "users.json") -> List[Dict[str, Any]]:
    """Load users from JSON file"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Users file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format in users file")

def find_top_3_interest_matches(user_id: str, json_path: str = r"users.json"):
    # Load users
    with open(json_path, "r", encoding="utf-8") as f:
        users = json.load(f)

    # Get target user
    target_user = next((u for u in users if u["id"] == user_id), None)
    if not target_user:
        raise ValueError(f"User with ID '{user_id}' not found.")

    target_interests = target_user.get("interests", [])
    if not target_interests:
        raise ValueError(f"User '{user_id}' has no interests.")

    matches = []

    for user in users:
        if user["id"] == user_id:
            continue

        other_interests = user.get("interests", [])
        if not other_interests:
            continue

        # Simple set intersection
        common_interests = set(target_interests) & set(other_interests)

        if not common_interests:
            continue

        score = len(common_interests)  # Matching score is just the number of shared interests

        matches.append({
            "user_id": user["id"],
            "name": user["full_name"],
            "email": user.get("email", "N/A"),
            "job_title": user.get("job_title", "N/A"),
            "company": user.get("company", "N/A"),
            "score": score,
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
    """Get all users data"""
    try:
        users = load_users()
        return users
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")