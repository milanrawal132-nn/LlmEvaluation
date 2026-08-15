"""Shared test setup.

The judge tests need OPENAI_API_KEY. Loading it here rather than inside each
test means a test can never pass "by accident" because some earlier test
happened to load the environment first.
"""

from pathlib import Path

from dotenv import load_dotenv

# Explicit path, not bare load_dotenv(): the no-argument form walks the call
# stack to find the caller's directory and raises when there is no frame.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
