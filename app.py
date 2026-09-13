from flask import Flask, jsonify, render_template
from flask_cors import CORS
from api.routes import api_bp

app = Flask(__name__)
# Enable CORS for the API routes so the frontend dev server can hit them
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:5000", "http://127.0.0.1:5173", "http://127.0.0.1:5000"]}})


app.register_blueprint(api_bp)

from flask import send_from_directory
import os

@app.route('/')
def index():
    return send_from_directory(os.path.join(app.root_path, 'static', 'dist'), 'index.html')

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
