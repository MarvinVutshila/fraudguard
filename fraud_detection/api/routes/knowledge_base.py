from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from fraud_detection.api.dependencies import verify_token
from fraud_detection.database.postgres_db import Database
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge_base", tags=["knowledge_base"])

class KBEntryCreate(BaseModel):
    question: str
    answer: str
    category: str = "General"
    keywords: str = ""

class KBEntryUpdate(BaseModel):
    question: str
    answer: str
    category: str
    keywords: str

@router.get("/")
async def list_entries(
    search: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(verify_token)
):
    """List knowledge base entries – accessible to any authenticated user."""
    # No admin check – any valid user can view
    db = Database()
    entries = db.get_knowledge_base_entries(search, limit, offset)
    total = db.count_knowledge_base_entries(search)
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}

@router.get("/{entry_id}")
async def get_entry(entry_id: int, user=Depends(verify_token)):
    """Get a single entry – accessible to any authenticated user."""
    db = Database()
    entry = db.get_knowledge_base_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    return entry

@router.post("/")
async def create_entry(entry: KBEntryCreate, user=Depends(verify_token)):
    """Create a new entry – admin only."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    db = Database()
    entry_id = db.create_knowledge_base_entry(
        question=entry.question,
        answer=entry.answer,
        category=entry.category,
        keywords=entry.keywords
    )
    return {"id": entry_id, "message": "Entry created"}

@router.put("/{entry_id}")
async def update_entry(entry_id: int, entry: KBEntryUpdate, user=Depends(verify_token)):
    """Update an entry – admin only."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    db = Database()
    updated = db.update_knowledge_base_entry(
        entry_id=entry_id,
        question=entry.question,
        answer=entry.answer,
        category=entry.category,
        keywords=entry.keywords
    )
    if not updated:
        raise HTTPException(404, "Entry not found")
    return {"message": "Entry updated"}

@router.delete("/{entry_id}")
async def delete_entry(entry_id: int, user=Depends(verify_token)):
    """Delete an entry – admin only."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    db = Database()
    deleted = db.delete_knowledge_base_entry(entry_id)
    if not deleted:
        raise HTTPException(404, "Entry not found")
    return {"message": "Entry deleted"}