"""
POST /api/grading/submit
Server-side gating: this endpoint re-checks user_progress in Supabase
before running any simulation. A locked topic returns 403 no matter what
the frontend sends — the UI lock is a convenience, this is the source of truth.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.grading.simulator import GateOp, grade
from app.deps import get_supabase, get_current_user_id  # implement per your auth flow

router = APIRouter()


class SubmitPayload(BaseModel):
    topic_id: str
    challenge_id: str
    num_qubits: int
    ops: list[GateOp]
    prediction: dict[str, float]


@router.post("/submit")
def submit(payload: SubmitPayload, user_id: str = Depends(get_current_user_id), sb=Depends(get_supabase)):
    # 1. gating check — never trust the frontend's locked/unlocked state
    topic = sb.table("topics").select("*").eq("id", payload.topic_id).single().execute().data
    if topic["prerequisite_id"]:
        prereq_progress = (
            sb.table("user_progress")
            .select("status")
            .eq("user_id", user_id)
            .eq("topic_id", topic["prerequisite_id"])
            .execute()
            .data
        )
        if not prereq_progress or prereq_progress[0]["status"] != "completed":
            raise HTTPException(403, "Prerequisite topic not completed")

    challenge = (
        sb.table("challenges").select("*").eq("id", payload.challenge_id).single().execute().data
    )

    result = grade(
        num_qubits=payload.num_qubits,
        ops=payload.ops,
        prediction=payload.prediction,
        tolerance_low=challenge["tolerance_low"],
        tolerance_high=challenge["tolerance_high"],
    )

    sb.table("user_progress").upsert(
        {
            "user_id": user_id,
            "topic_id": payload.topic_id,
            "status": "completed" if result.correct else "in_progress",
            "submitted_prediction": payload.prediction,
            "graded_result": {
                "measured_distribution": result.measured_distribution,
                "correct": result.correct,
                "per_outcome_deltas": result.per_outcome_deltas,
            },
        },
        on_conflict="user_id,topic_id",
    ).execute()

    return result
