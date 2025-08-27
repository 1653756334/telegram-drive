#!/usr/bin/env python3
"""Run the new modern Telegram Drive backend."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app_new.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
