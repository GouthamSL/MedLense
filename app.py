"""MedLense Healthcare Hackathon Backend Application.

Main entry point providing FastAPI application, CORS middleware,
system health endpoints, and routing for Prescription Intelligence.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.prescription_intelligence.router import router as prescription_router

app = FastAPI(
    title="MedLense API",
    description="Prescription Intelligence and Medication Safety Backend Engine",
    version="1.0.0",
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include module routers
app.include_router(prescription_router, prefix="/api/v1")
app.include_router(prescription_router, prefix="/api")  # Convenience alias


@app.get("/", summary="Root Status")
async def root():
    return {
        "project": "MedLense",
        "description": "Prescription Intelligence & Medication Safety System",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "prescription_extract": "/api/v1/prescription/extract",
            "prescription_upload": "/api/v1/prescription/upload",
            "prescription_health": "/api/v1/prescription/health",
            "docs": "/docs",
        },
    }


@app.get("/health", summary="Overall Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": "MedLense Backend",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

