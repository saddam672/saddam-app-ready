import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from a2wsgi import ASGIMiddleware
from main import app

# Phusion Passenger WSGI entry point
application = ASGIMiddleware(app)
