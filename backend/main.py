from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  
from api import router
from drafting import router as drafting_router
from classifier import router as classifier_router
from consistency import router as consistency_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sherpa — SME IPO Drafting Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(drafting_router)
app.include_router(classifier_router)
app.include_router(consistency_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "sherpa-backend"}