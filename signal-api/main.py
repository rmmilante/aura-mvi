from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="AURA Signal API", version="0.1.0")

readings_history: Dict[str, List[dict]] = {}
anomaly_count: int = 0

class TagReading(BaseModel):
    tag_id: str
    value: float
    unit: str
    timestamp: str

class IngestPayload(BaseModel):
    asset: str
    readings: List[TagReading]

@app.post("/ingest")
def ingest(payload: IngestPayload):
    global anomaly_count
    
    for reading in payload.readings:
        if reading.tag_id not in readings_history:
            readings_history[reading.tag_id] = []
        
        readings_history[reading.tag_id].append({
            "value": reading.value,
            "timestamp": reading.timestamp
        })
        
        if len(readings_history[reading.tag_id]) > 60:
            readings_history[reading.tag_id].pop(0)
        
        if reading.tag_id == "P101_TEMP" and reading.value > 85:
            anomaly_count += 1
        elif reading.tag_id == "P101_VIBRATION" and reading.value > 5:
            anomaly_count += 1
    
    return {"status": "ingested", "asset": payload.asset, "anomalies": anomaly_count}

@app.get("/status")
def status():
    latest = {}
    for tag_id, history in readings_history.items():
        if history:
            latest[tag_id] = history[-1]
    
    return {
        "status": "up",
        "anomalies_detected": anomaly_count,
        "latest_readings": latest
    }

@app.get("/health")
def health():
    return {"status": "up", "service": "signal-api"}