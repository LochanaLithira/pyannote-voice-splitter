from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, jobs, speakers, download

app = FastAPI(title="Sales Call Splitter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,   prefix="/api")
app.include_router(jobs.router,     prefix="/api")
app.include_router(speakers.router, prefix="/api")
app.include_router(download.router, prefix="/api")