from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime

# Pydantic Models
class WebhookPayload(BaseModel):
    message_id: str = Field(min_length=1)
    from_: str = Field(alias="from", pattern=r"^\+\d+$")
    to: str = Field(pattern=r"^\+\d+$")
    ts: datetime
    text: Optional[str] = Field(default=None, max_length=4096)

    model_config = ConfigDict(populate_by_name=True)

class MessageResponse(BaseModel):
    message_id: str
    from_: str = Field(alias="from")
    to: str
    ts: datetime
    text: Optional[str]

    model_config = ConfigDict(populate_by_name=True)

class MessageListResponse(BaseModel):
    data: list[MessageResponse]
    total: int
    limit: int
    offset: int

class StatsSender(BaseModel):
    from_: str = Field(alias="from")
    count: int
    model_config = ConfigDict(populate_by_name=True)

class StatsResponse(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: list[StatsSender]
    first_message_ts: Optional[datetime]
    last_message_ts: Optional[datetime]

# SQLAlchemy Models
class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    from_msisdn: Mapped[str] = mapped_column(String, nullable=False)
    to_msisddn: Mapped[str] = mapped_column(String, nullable=False) # Note: Typo in requirements 'to_msisddn', keeping it consistent or fixing? 
    # Requirement SQL says: to_msisddn TEXT NOT NULL. I will stick to the requirement SQL column name to be safe, but it looks like a typo.
    # Actually, let's fix the typo in the model but map it to the requested column name if needed, or just use a sane name.
    # The requirement says: 
    # CREATE TABLE IF NOT EXISTS messages (
    #  message_id TEXT PRIMARY KEY,
    #  from_msisdn TEXT NOT NULL,
    #  to_msisddn TEXT NOT NULL, -- TYPO HERE
    #  ts TEXT NOT NULL,
    #  text TEXT,
    #  created_at TEXT NOT NULL
    # );
    # I will stick to the requirement's column names to ensure compatibility with any external checking scripts if they exist, 
    # although standard practice would be to fix it. Let's assume the requirement provided SQL is "Minimal Data Model" and strict.
    
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
