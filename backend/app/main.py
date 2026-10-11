"""
FastAPI application for Mineral Exploration and Analysis System.
Exposes REST endpoints:
- GET /health
- GET /minerals
- POST /analyze
- POST /classify-image
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend root and app directory are on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.mineral_service import (
    SUPPORTED_MINERALS,
    get_mineral_registry,
    analyze_location_for_mineral,
    get_candidate_zones_list,
    get_satellite_scenes_for_location,
    get_production_forecast_data,
)
from app.vision_service import classify_specimen_image

app = FastAPI(
    title="Mineral Exploration and Analysis API",
    description="Integrated API for geographical mineral prospectivity analysis and 4-class specimen classification.",
    version="1.0.0",
)

# CORS configuration for development frontend origins
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    location_name: str = Field(..., description="Selected place or region name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    mineral: str = Field(..., description="Target mineral: Coal, Manganese, Iron Ore, or Bauxite")
    radius_km: float = Field(..., gt=0, le=100, description="Search radius in kilometers: 1, 5, 10, or 25")
    mock_satellite_error: Optional[str] = Field(None, description="Optional testing hook for simulated satellite catalogue error states")


@app.get("/health")
def health_check():
    """Returns system status, active models, and available services."""
    model_path = os.path.join(project_root, "models", "mineral_image_classifier.pth")
    manganese_rf_path = os.path.join(project_root, "models", "manganese_random_forest.pkl")

    return {
        "status": "healthy",
        "service": "Mineral Exploration and Analysis System",
        "supported_mineral_classes": SUPPORTED_MINERALS,
        "image_classifier_available": os.path.exists(model_path),
        "manganese_geographical_model_available": os.path.exists(manganese_rf_path),
        "version": "1.0.0",
    }


@app.get("/minerals")
def get_minerals():
    """Returns the list and metadata of the exactly four supported mineral classes."""
    return {
        "minerals": get_mineral_registry(),
        "total_classes": len(SUPPORTED_MINERALS),
    }


@app.get("/candidate-zones")
def get_candidate_zones():
    """Returns the 20 verified high-prospectivity anomaly zones from Sentinel-2 Random Forest model."""
    zones = get_candidate_zones_list()
    return {
        "candidate_zones": zones,
        "total_zones": len(zones),
        "tile": "T44QMK",
        "region": "Balaghat-Nagpur-Bhandara Manganese Belt",
    }


@app.get("/satellite-scenes")
def get_satellite_scenes(latitude: float, longitude: float, mineral: str = "Manganese", mock_error: Optional[str] = None):
    """Discovers available Copernicus Sentinel-2 satellite scenes for the target coordinates."""
    discovery = get_satellite_scenes_for_location(latitude, longitude, mineral, mock_error_type=mock_error)
    scenes = discovery.get("scenes", [])
    return {
        "latitude": latitude,
        "longitude": longitude,
        "mineral": mineral,
        "scenes": scenes,
        "total_scenes": len(scenes),
        "availability_status": discovery.get("status"),
        "source": discovery.get("source"),
        "error_details": discovery.get("error_details")
    }


@app.get("/production-forecast")
def get_production_forecast(mineral: str = "Manganese"):
    """Returns historical production shortfalls and operational telemetry analysis."""
    return get_production_forecast_data(mineral)



@app.post("/analyze")
def analyze_location(req: AnalyzeRequest):
    """
    Analyzes geographical mineral prospectivity for a given coordinate, mineral class, and radius.
    Strictly distinguishes between genuine data and missing data.
    """
    valid_radii = [1.0, 5.0, 10.0, 25.0]
    if req.radius_km not in valid_radii and req.radius_km not in [1, 5, 10, 25]:
        # Accept close values but standard choices are 1, 5, 10, 25
        pass

    try:
        result = analyze_location_for_mineral(
            location_name=req.location_name,
            lat=req.latitude,
            lon=req.longitude,
            mineral_name=req.mineral,
            radius_km=req.radius_km,
            mock_satellite_error=req.mock_satellite_error
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(exc)}")


@app.post("/classify-image")
async def classify_image(file: UploadFile = File(...)):
    """
    Performs rock specimen image classification among the 4 classes:
    Coal, Manganese, Iron Ore, Bauxite.
    Uses the trained PyTorch MineralConvNet model.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image (JPEG, PNG, WebP).",
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(contents) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Uploaded file exceeds 15MB limit.")

        result = classify_specimen_image(contents)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Specimen classification failed: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
