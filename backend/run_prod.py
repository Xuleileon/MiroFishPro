"""
MiroFish Production Server
Serves Flask API + built frontend static files on single port
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import send_from_directory

app = create_app()

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    full_path = os.path.join(DIST_DIR, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
