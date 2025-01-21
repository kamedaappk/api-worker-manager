from flask import Flask, request, jsonify, send_file, render_template
import json
import os
import uuid
import requests
import threading
import time

app = Flask(__name__)

# Directory to store worker files
WORKERS_DIR = "workers"
os.makedirs(WORKERS_DIR, exist_ok=True)

# Load worker data from file
def load_worker(worker_id):
    worker_file = os.path.join(WORKERS_DIR, f"worker_{worker_id}.json")
    if os.path.exists(worker_file):
        with open(worker_file, "r") as file:
            return json.load(file)
    return None

# Save worker data to file
def save_worker(worker):
    worker_file = os.path.join(WORKERS_DIR, f"worker_{worker['id']}.json")
    with open(worker_file, "w") as file:
        json.dump(worker, file, indent=4)

# Validate an endpoint
def validate_endpoint(endpoint):
    try:
        response = requests.get(endpoint)
        return response.status_code == 200
    except:
        return False

# Generate a unique ID for a worker
def generate_id():
    return str(uuid.uuid4())

# Background task for a worker
def worker_task(worker_id, endpoint, frequency, total_calls):
    frequency = int(frequency)  # Ensure frequency is an integer
    while True:
        worker = load_worker(worker_id)
        if not worker or worker["status"] != "running" or worker["remaining_calls"] <= 0:
            break  # Stop if worker is deleted, stopped, or out of calls

        # Make the API call
        try:
            response = requests.get(endpoint)
            if response.status_code == 200:
                print(f"Worker {worker_id}: Call successful")
            else:
                print(f"Worker {worker_id}: Call failed with status {response.status_code}")
        except Exception as e:
            print(f"Worker {worker_id}: Error - {e}")

        # Update remaining calls
        worker["remaining_calls"] -= 1
        save_worker(worker)

        # Sleep for the specified frequency
        time.sleep(frequency)

# Serve the main UI
@app.route("/")
def index():
    return render_template("index.html")

# List all workers
@app.route("/workers", methods=["GET"])
def list_workers():
    workers = []
    for filename in os.listdir(WORKERS_DIR):
        if filename.startswith("worker_") and filename.endswith(".json"):
            with open(os.path.join(WORKERS_DIR, filename), "r") as file:
                workers.append(json.load(file))
    return jsonify({"workers": workers})  # Ensure the response has a "workers" key

# Validate a worker's endpoint
@app.route("/workers/validate", methods=["POST"])
def validate_worker():
    data = request.json
    endpoint = data.get("endpoint")
    if not endpoint:
        return jsonify({"error": "Endpoint is required"}), 400

    is_valid = validate_endpoint(endpoint)
    return jsonify({"endpoint": endpoint, "is_valid": is_valid})

# Add a new worker
@app.route("/workers", methods=["POST"])
def add_worker():
    data = request.json
    endpoint = data.get("endpoint")
    if not endpoint:
        return jsonify({"error": "Endpoint is required"}), 400

    worker_id = generate_id()
    worker = {
        "id": worker_id,
        "endpoint": endpoint,
        "frequency": int(data.get("frequency", 60)),  # Ensure frequency is an integer
        "total_calls": int(data.get("total_calls", 100)),  # Ensure total_calls is an integer
        "remaining_calls": int(data.get("total_calls", 100)),  # Ensure remaining_calls is an integer
        "is_valid": validate_endpoint(endpoint),
        "status": "stopped",  # Default status: stopped
    }
    save_worker(worker)
    return jsonify(worker), 201

# Start a worker
@app.route("/workers/<worker_id>/start", methods=["POST"])
def start_worker(worker_id):
    worker = load_worker(worker_id)
    if not worker:
        return jsonify({"error": "Worker not found"}), 404

    if worker["status"] == "running":
        return jsonify({"error": "Worker is already running"}), 400

    worker["status"] = "running"
    save_worker(worker)

    # Start the worker in a background thread
    threading.Thread(
        target=worker_task,
        args=(worker_id, worker["endpoint"], worker["frequency"], worker["total_calls"]),
        daemon=True,
    ).start()

    return jsonify({"message": "Worker started"})

# Stop a worker
@app.route("/workers/<worker_id>/stop", methods=["POST"])
def stop_worker(worker_id):
    worker = load_worker(worker_id)
    if not worker:
        return jsonify({"error": "Worker not found"}), 404

    if worker["status"] == "stopped":
        return jsonify({"error": "Worker is already stopped"}), 400

    worker["status"] = "stopped"
    save_worker(worker)
    return jsonify({"message": "Worker stopped"})

# Edit worker details
@app.route("/workers/<worker_id>/edit", methods=["PUT"])
def edit_worker(worker_id):
    data = request.json
    worker = load_worker(worker_id)
    if not worker:
        return jsonify({"error": "Worker not found"}), 404

    if worker["status"] == "running":
        return jsonify({"error": "Cannot edit a running worker"}), 400

    worker["endpoint"] = data.get("endpoint", worker["endpoint"])
    worker["frequency"] = int(data.get("frequency", worker["frequency"]))  # Ensure frequency is an integer
    worker["total_calls"] = int(data.get("total_calls", worker["total_calls"]))  # Ensure total_calls is an integer
    worker["remaining_calls"] = int(data.get("total_calls", worker["total_calls"]))  # Ensure remaining_calls is an integer
    worker["is_valid"] = validate_endpoint(worker["endpoint"])
    save_worker(worker)
    return jsonify(worker)

# Delete a worker
@app.route("/workers/<worker_id>", methods=["DELETE"])
def delete_worker(worker_id):
    worker = load_worker(worker_id)
    if not worker:
        return jsonify({"error": "Worker not found"}), 404

    if worker["status"] == "running":
        return jsonify({"error": "Cannot delete a running worker"}), 400

    worker_file = os.path.join(WORKERS_DIR, f"worker_{worker_id}.json")
    if os.path.exists(worker_file):
        os.remove(worker_file)
        return jsonify({"message": "Worker deleted"})
    return jsonify({"error": "Worker file not found"}), 404

# Export workers to a JSON file
@app.route("/workers/export", methods=["GET"])
def export_workers():
    workers = []
    for filename in os.listdir(WORKERS_DIR):
        if filename.startswith("worker_") and filename.endswith(".json"):
            with open(os.path.join(WORKERS_DIR, filename), "r") as file:
                workers.append(json.load(file))
    export_file = os.path.join(WORKERS_DIR, "workers_export.json")
    with open(export_file, "w") as file:
        json.dump({"workers": workers}, file, indent=4)
    return send_file(export_file, as_attachment=True)

# Import workers from a JSON file
@app.route("/workers/import", methods=["POST"])
def import_workers():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        data = json.load(file)
        for worker in data.get("workers", []):
            save_worker(worker)
        return jsonify({"message": "Workers imported successfully"})
    except:
        return jsonify({"error": "Invalid JSON file"}), 400

# Run the app
if __name__ == "__main__":
    app.run(debug=True)