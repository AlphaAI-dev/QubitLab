from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.chatbot.provider import get_chat_provider
from app.chatbot.rag import retrieve_context
from app.deps import get_current_user_id, get_supabase

router = APIRouter()


class ChatPayload(BaseModel):
    session_id: str
    message: str
    topic_id: str | None = None


@router.post("/message")
async def send_message(payload: ChatPayload, user_id: str = Depends(get_current_user_id), sb=Depends(get_supabase)):
    context = retrieve_context(payload.message, topic_id=payload.topic_id)
    provider = get_chat_provider()
    reply = await provider.complete(payload.message, context)

    sb.table("chat_messages").insert(
        [
            {"session_id": payload.session_id, "role": "user", "content": payload.message},
            {"session_id": payload.session_id, "role": "assistant", "content": reply},
        ]
    ).execute()

    return {"reply": reply}
