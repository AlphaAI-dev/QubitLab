import os
from functools import lru_cache
from fastapi import Header, HTTPException
from supabase import create_client, Client


@lru_cache
def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_current_user_id(authorization: str = Header(...)) -> str:
    """
    Verifies the Supabase JWT passed from the frontend and returns the user id.
    Real implementation calls sb.auth.get_user(token) — stubbed here for scaffold clarity.
    """
    token = authorization.replace("Bearer ", "")
    sb = get_supabase()
    user = sb.auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user.user.id
