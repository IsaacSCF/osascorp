from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, orgs, websocket
from app.database import Base, engine
import os

# Create database tables
Base.metadata.create_all(bind=engine)

# Detect environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Production CORS - allow specific origins
    ALLOWED_ORIGINS = [
        "https://orgs-frontend.vercel.app",
        "https://orgs-frontend.netlify.app",
        "https://orgs-frontend.pages.dev",
        os.getenv("FRONTEND_URL", "")
    ]
    ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]  # Remove empty strings
else:
    # Development CORS - allow all
    ALLOWED_ORIGINS = ["*"]

app = FastAPI(
    title="Sistema de Organização de Orgs",
    description="API para gerenciamento de organizações legais e ilegais com sincronização em tempo real",
    version="1.0.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/auth", tags=["authentication"])
app.include_router(orgs.router, prefix="/orgs", tags=["organizations"])
app.include_router(websocket.router, tags=["websockets"])

@app.get("/")
def read_root():
    return {"message": "Sistema de Organização de Orgs - API Online"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Use a porta definida pelo Railway
    uvicorn.run(app, host="0.0.0.0", port=port)
