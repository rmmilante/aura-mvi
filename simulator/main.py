from fastapi import FastAPI
from pydantic import BaseModel
import random
import time
from datetime import datetime

app = FastAPI(title="AURA Pump Simulator", version="0.1.0")

# Pump P-101 state
state = {
    "fault_injected": False,
    "start_time": time.time(),
}

class TagReading(BaseModel):
    tag_id: str
    value: float
    unit: str
    timestamp: str

class TagsResponse(BaseModel):
    asset: str
    readings: list[TagReading]

def generate_reading(tag_id: str, base: float, noise: float, fault_mult: float, unit: str) -> TagReading:
    elapsed = time.time() - state["start_time"]
    
    # Normal drift: random walk + slight sine-like drift
    drift = base + (noise * random.gauss(0, 1)) + (0.5 * noise * (elapsed % 60) / 60)
    
    # Fault mode: spike the value
    if state["fault_injected"]:
        drift *= fault_mult
    
    return TagReading(
        tag_id=tag_id,
        value=round(drift, 2),
        unit=unit,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

@app.get("/tags", response_model=TagsResponse)
def get_tags():
    return TagsResponse(
        asset="P-101",
        readings=[
            generate_reading("P101_TEMP", 75.0, 2.0, 1.35, "degC"),
            generate_reading("P101_VIBRATION", 2.1, 0.3, 3.8, "mm/s"),
            generate_reading("P101_PRESSURE", 4.2, 0.15, 1.1, "bar"),
        ]
    )

@app.post("/inject-fault")
def inject_fault():
    state["fault_injected"] = True
    return {"status": "fault_injected", "asset": "P-101", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/clear-fault")
def clear_fault():
    state["fault_injected"] = False
    state["start_time"] = time.time()
    return {"status": "fault_cleared", "asset": "P-101"}

@app.get("/health")
def health():
    return {"status": "up", "asset": "P-101"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
