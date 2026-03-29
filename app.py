"""
app.py - Flask Backend for Desmos V2
=====================================
High-density image-to-polygon vectorization
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from modules.processor import process_image, generate_desmos_script

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


@app.route("/api/process", methods=["POST"])
def process():
    """Process image and return vectorized polygons"""
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"success": False, "error": "No image provided"}), 400

        image_data = data["image"]
        epsilon = data.get("epsilon", 0.0001)  # 0.0001 = Maximum density
        num_colors = data.get("num_colors", 256)  # Max colors
        min_area = data.get("min_area", 0)  # No minimum

        processed = process_image(
            image_data, epsilon=epsilon, num_colors=num_colors, min_area=min_area
        )

        desmos_script = generate_desmos_script(processed)

        return jsonify(
            {
                "success": True,
                "data": {
                    "stats": processed["stats"],
                    "desmos_script": desmos_script,
                    "polygon_count": processed["stats"]["total_polygons"],
                    "background_color": processed["background_color"],
                },
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "desmos-v2"})


if __name__ == "__main__":
    print("=" * 60)
    print("  Desmos V2 - 1:1 Visual Parity Pipeline")
    print("  Running on http://localhost:5556")
    print("  RDP Epsilon: 0.0001 | Colors: 256 | Precision: 4")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5556, debug=True)
