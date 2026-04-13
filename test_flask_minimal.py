#!/usr/bin/env python3
"""Minimal Flask app to test if Flask works"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Flask!'

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    print("Starting minimal Flask app on port 5000...")
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
