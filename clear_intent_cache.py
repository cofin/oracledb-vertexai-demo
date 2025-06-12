#!/usr/bin/env python
"""Clear the intent exemplar cache to force re-embedding with new exemplars."""

import asyncio
from app.lib.settings import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def clear_intent_cache():
    """Clear all cached intent exemplars."""
    settings = get_settings()
    engine = settings.db.get_engine()
    
    async with engine.connect() as conn:
        # Delete all intent exemplars
        result = await conn.execute(text("DELETE FROM intent_exemplar"))
        await conn.commit()
        
        count = result.rowcount
        print(f"Cleared {count} cached intent exemplars")
        print("The next chat request will re-populate the cache with all new exemplars")


if __name__ == "__main__":
    asyncio.run(clear_intent_cache())