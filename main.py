"""
FastAPI service — owns everything that touches Qiskit:
circuit validation, simulation-based grading, and RAG context assembly
for the chatbot. Nothing here trusts frontend state; gating and correctness
checks are re-verified server-side (see app/routers/grading.py).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import grading, chat

app = FastAPI(title="Quantum Learning Platform — Grading & Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin per environment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grading.router, prefix="/api/grading", tags=["grading"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/health")
def health():
    return {"status": "ok"}
