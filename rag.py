"""
Light RAG, deliberately not a vector DB. Five topics, each a short markdown
explanation — a keyword-overlap retrieval over ~5 documents outperforms the
operational cost of standing up a vector store for this corpus size.
Revisit only if the curriculum grows past ~30-40 topics.
"""
from app.deps import get_supabase


def retrieve_context(query: str, topic_id: str | None = None, k: int = 2) -> str:
    sb = get_supabase()

    if topic_id:
        # if the learner is asking from within a specific topic page, bias hard to it
        topic = sb.table("topics").select("title,explanation_md").eq("id", topic_id).single().execute().data
        return f"## {topic['title']}\n{topic['explanation_md']}"

    topics = sb.table("topics").select("title,explanation_md").execute().data
    query_words = set(query.lower().split())

    scored = sorted(
        topics,
        key=lambda t: len(query_words & set(t["explanation_md"].lower().split())),
        reverse=True,
    )
    top = scored[:k]
    return "\n\n".join(f"## {t['title']}\n{t['explanation_md']}" for t in top)
