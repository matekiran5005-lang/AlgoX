"""
WSGI entry point for production deployment.

Usage:
    gunicorn -w 4 -b 0.0.0.0:3000 wsgi:app
"""
import logging
from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app, engine = create_app()
engine.start_scheduler()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)