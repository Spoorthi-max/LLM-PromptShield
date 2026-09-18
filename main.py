from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os

from security.pipeline import pipeline
from adversarial.graph import adversarial_app

app = FastAPI(title="Antigravity-Shield", version="3.0")

# Global history for the UI
event_logs = []

class EvaluateRequest(BaseModel):
    raw_input: str
    history: Optional[List[str]] = None

@app.get("/logs")
async def get_logs():
    return event_logs

@app.post("/evaluate")
async def evaluate_input(request: EvaluateRequest):
    try:
        result = pipeline.run_security_checks(request.raw_input, request.history)
        event_logs.append({
            "type": "EVALUATION",
            "input": request.raw_input,
            "history": request.history,
            "result": result
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/adversarial-loop")
async def run_adversarial_loop():
    initial_state = {
        "history": [],
        "iterations": 0
    }
    
    try:
        final_state = adversarial_app.invoke(initial_state)
        
        # Log each step of the battle
        for step in final_state.get("full_history", []):
            event_logs.append({
                "type": "ADVERSARIAL_STEP",
                "iteration": step["iteration"],
                "attack": step["attack"],
                "result": step["result"]
            })

        event_logs.append({
            "type": "ADVERSARIAL_LOOP_COMPLETE",
            "iterations": final_state.get("iterations"),
            "final_attack": final_state.get("current_attack"),
            "final_patch": final_state.get("last_patch")
        })
        
        return {
            "status": "COMPLETED",
            "iterations": final_state.get("iterations"),
            "full_history": final_state.get("full_history"),
            "final_patch": final_state.get("last_patch")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount Static Files (Dashboard)
# Ensure the directory exists
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
