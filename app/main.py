"""Entry point. Start the server with:

    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

The tests never import this file, so they never create the real database.
"""

from app.application import create_app

app = create_app()
