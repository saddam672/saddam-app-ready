"""
Legal versioning.

Bump TERMS_VERSION (env var) whenever you change Terms / Privacy / Risk text.
Every user must then accept the new version again before trading.
"""
import os

TERMS_VERSION = os.getenv("TERMS_VERSION", "1.0")
