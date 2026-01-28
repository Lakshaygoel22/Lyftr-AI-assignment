from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func, desc, text
from app.config import get_settings
from app.models import Base, Message, WebhookPayload

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class Storage:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_message(self, message_id: str) -> Optional[Message]:
        result = await self.session.execute(select(Message).where(Message.message_id == message_id))
        return result.scalar_one_or_none()

    async def create_message(self, payload: WebhookPayload) -> Message:
        message = Message(
            message_id=payload.message_id,
            from_msisdn=payload.from_,
            to_msisddn=payload.to,
            ts=payload.ts,
            text=payload.text
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(self, limit: int, offset: int, from_filter: Optional[str] = None, since_filter: Optional[str] = None, q_filter: Optional[str] = None) -> tuple[List[Message], int]:
        query = select(Message)
        
        if from_filter:
            query = query.where(Message.from_msisdn == from_filter)
        
        if since_filter:
            # Assuming since_filter is passed as a generic string, but we should parse it in the route. 
            # If it's passed as datetime here:
            query = query.where(Message.ts >= since_filter)
            
        if q_filter:
            query = query.where(Message.text.ilike(f"%{q_filter}%"))

        # Count total matches before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # Ordering
        query = query.order_by(Message.ts.asc(), Message.message_id.asc())
        
        # Pagination
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def get_stats(self):
        total_messages = await self.session.scalar(select(func.count(Message.message_id)))
        senders_count = await self.session.scalar(select(func.count(func.distinct(Message.from_msisdn))))
        
        start_ts = await self.session.scalar(select(func.min(Message.ts)))
        end_ts = await self.session.scalar(select(func.max(Message.ts)))
        
        # Top 10 senders
        senders_query = select(
            Message.from_msisdn, 
            func.count(Message.message_id).label("count")
        ).group_by(Message.from_msisdn).order_by(desc("count")).limit(10)
        
        senders_result = await self.session.execute(senders_query)
        messages_per_sender = [{"from": row[0], "count": row[1]} for row in senders_result]

        return {
            "total_messages": total_messages or 0,
            "senders_count": senders_count or 0,
            "messages_per_sender": messages_per_sender,
            "first_message_ts": start_ts,
            "last_message_ts": end_ts
        }
