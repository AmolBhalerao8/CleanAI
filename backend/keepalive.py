"""
Keep-alive background task.
Pings /health every 10 minutes so Render free tier never sleeps.
Only runs when BASE_URL is set to a real public URL.
"""
import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def start_keepalive():
    base_url = os.getenv("BASE_URL", "")
    if not base_url or "localhost" in base_url:
        logger.info("Keep-alive disabled (no public BASE_URL set).")
        return

    url = f"{base_url}/health"
    logger.info("Keep-alive started — pinging %s every 10 minutes.", url)

    while True:
        await asyncio.sleep(600)  # 10 minutes
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                logger.info("Keep-alive ping: %s", resp.status_code)
        except Exception as exc:
            logger.warning("Keep-alive ping failed: %s", exc)
