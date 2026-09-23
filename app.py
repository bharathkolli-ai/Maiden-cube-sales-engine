from flask import Flask, jsonify
import asyncio
from stage1_pipeline import main as run_stage1_pipeline

app = Flask(__name__)

@app.route("/run-stage1", methods=["POST"])
def run_stage1():
    try:
        results = asyncio.run(run_stage1_pipeline())
        return jsonify({"status": "success", "count": len(results), "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)