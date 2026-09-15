"""Query / chat API endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ready_repository
from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.answering import AnswerGenerator
from app.llm.factory import get_llm_provider
from app.models.orm import Conversation, Message, Repository
from app.retrieval.engine import RetrievalEngine
from app.schemas.query import (
    Citation,
    ConversationCreate,
    ConversationRead,
    MessageRead,
    QueryRequest,
    QueryResponse,
)

router = APIRouter(prefix="/repositories/{repository_id}", tags=["query"])
logger = get_logger(__name__)


def _get_engine() -> RetrievalEngine:
    return RetrievalEngine(get_settings())


@router.post("/query", response_model=QueryResponse)
def query_repository(
    body: QueryRequest,
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    """Ask a natural-language question about the indexed repository."""
    cfg = get_settings()
    engine = _get_engine()

    # Retrieve conversation history for context
    history: list[dict] = []
    conversation_id = body.conversation_id
    conversation = None

    if conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.repository_id == repo.id,  # isolation
            )
            .first()
        )
        if conversation:
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .limit(10)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in msgs]

    # Create conversation if not provided
    if not conversation:
        conversation = Conversation(
            repository_id=repo.id,
            title=body.question[:80],
        )
        db.add(conversation)
        db.flush()
        conversation_id = conversation.id

    # ── Retrieval ──────────────────────────────────────────────────────
    retrieval = engine.retrieve(
        db=db,
        repository_id=repo.id,
        query=body.question,
        repository_name=repo.name,
    )

    # ── Answer generation ──────────────────────────────────────────────
    graph_data = None
    if body.include_graph:
        try:
            from app.graph.service import get_graph  # noqa: PLC0415
            graph = get_graph(db, repo.id)
            primary_ids = [
                c.get("payload", {}).get("symbol_id") or c["id"]
                for c in retrieval.candidates[:5]
            ]
            graph_data = graph.subgraph_for_visualization(primary_ids, depth=2, limit=40)
        except Exception as exc:
            logger.warning("graph_viz_failed", extra={"error": str(exc)})

    try:
        llm = get_llm_provider(cfg)
        generator = AnswerGenerator(llm)
        result = generator.generate(retrieval, conversation_history=history)
    except Exception as exc:
        logger.error("answer_generation_error", extra={"error": str(exc)})
        # Graceful degradation
        citations_data = retrieval.citations()
        evidence = "\n".join(
            f"• {c['symbol_name']} @ {c['file_path']}:{c['start_line']}"
            for c in citations_data[:8]
        )
        result = {
            "answer": f"Answer generation unavailable ({exc}). Retrieved evidence:\n{evidence}",
            "citations": citations_data,
            "intent": retrieval.analysis.intent,
            "confidence": "NOT_FOUND",
            "retrieval_stats": retrieval.stats,
        }

    # ── Persist messages ───────────────────────────────────────────────
    citations_json = json.dumps(result.get("citations", []))
    db.add(Message(
        conversation_id=conversation_id,
        repository_id=repo.id,
        role="user",
        content=body.question,
    ))
    db.add(Message(
        conversation_id=conversation_id,
        repository_id=repo.id,
        role="assistant",
        content=result["answer"],
        citations_json=citations_json,
    ))
    db.commit()

    citations = [Citation(**c) for c in result.get("citations", []) if c.get("file_path")]

    return QueryResponse(
        answer=result["answer"],
        citations=citations,
        intent=result.get("intent", ""),
        confidence=str(result.get("confidence", "")),
        conversation_id=conversation_id,
        retrieval_stats=result.get("retrieval_stats", {}),
        graph_data=graph_data,
    )


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    convos = (
        db.query(Conversation)
        .filter(Conversation.repository_id == repo.id)
        .order_by(Conversation.created_at.desc())
        .limit(50)
        .all()
    )
    return convos


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def get_conversation_messages(
    conversation_id: str,
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.repository_id == repo.id,  # isolation
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    result = []
    for m in msgs:
        citations = []
        if m.citations_json:
            try:
                raw = json.loads(m.citations_json)
                citations = [Citation(**c) for c in raw if c.get("file_path")]
            except Exception:
                pass
        result.append(MessageRead(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=citations,
        ))
    return result
