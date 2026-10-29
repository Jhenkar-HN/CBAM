from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.db.seed import seed_database
from app.api.document_router import router as document_router
from app.api.calculation_router import router as calculation_router
from app.api.reporting_router import router as reporting_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed Baseline Data on startup
    init_db()
    seed_database()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Deterministic Decision-Support Platform for CBAM Emissions Compliance (Indian MSMEs)",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(document_router, prefix=settings.API_V1_STR)
app.include_router(calculation_router, prefix=settings.API_V1_STR)
app.include_router(reporting_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
