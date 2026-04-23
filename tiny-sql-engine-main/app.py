import os
import time
from flask import Flask, request, jsonify, send_from_directory

from pager import Pager
from models import Row
from sequential import SequentialEngine
from hash_engine import HashEngine
from btree_engine import BTreeEngine

app = Flask(__name__, static_folder=".")



seq_pager    = Pager("sequential_data.db")
hash_pager   = Pager("hash_data.db")
btree_pager  = Pager("btree_data.db")

seq_engine   = SequentialEngine(seq_pager)
hash_engine  = HashEngine(hash_pager)
btree_engine = BTreeEngine(btree_pager)

ENGINES = {
    "sequential": (seq_engine,   seq_pager),
    "hash":       (hash_engine,  hash_pager),
    "btree":      (btree_engine, btree_pager),
}

def _resolve(method: str):
    """Return (engine, pager) for the requested method string."""
    key = method.strip().lower()
    if key not in ENGINES:
        return None, None
    return ENGINES[key]



@app.route("/")
def index():
    return send_from_directory(".", "index.html")



@app.route("/api/insert", methods=["POST"])
def api_insert():
    data   = request.get_json(force=True)
    method = data.get("method", "sequential")
    engine, pager = _resolve(method)

    if engine is None:
        return jsonify({"error": f"Unknown method '{method}'"}), 400

    try:
        row_id   = int(data["id"])
        username = str(data.get("name", ""))
        email    = str(data.get("email", ""))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": f"Bad input: {exc}"}), 400

    row = Row(row_id, username, email)

    t0 = time.perf_counter()
    engine.insert(row)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return jsonify({
        "success": True,
        "method":  method,
        "time_ms": round(elapsed_ms, 4),
    })



@app.route("/api/find", methods=["POST"])
def api_find():
    data   = request.get_json(force=True)
    method = data.get("method", "sequential")
    engine, pager = _resolve(method)

    if engine is None:
        return jsonify({"error": f"Unknown method '{method}'"}), 400

    try:
        search_id = int(data["id"])
    except (KeyError, ValueError) as exc:
        return jsonify({"error": f"Bad input: {exc}"}), 400

    # ---- Benchmark exactly as specified ----
    start_reads = pager.read_count
    t0          = time.perf_counter()
    row         = engine.find(search_id)
    elapsed_ms  = (time.perf_counter() - t0) * 1000
    pages_read  = pager.read_count - start_reads

    try:
        file_size_kb = round(os.path.getsize(pager.filename) / 1024, 2)
    except OSError:
        file_size_kb = 0

    if row is None:
        return jsonify({
            "found":       False,
            "method":      method,
            "time_ms":     round(elapsed_ms, 4),
            "pages_read":  pages_read,
            "file_size_kb": file_size_kb,
        })

    # row.username / row.email are bytes inside the Row object — decode before JSON
    def _to_str(val):
        if isinstance(val, bytes):
            return val.decode('utf-8', errors='replace').rstrip('\x00')
        return str(val).rstrip('\x00')

    return jsonify({
        "found":        True,
        "method":       method,
        "id":           row.id,
        "name":         _to_str(row.username),
        "email":        _to_str(row.email),
        "time_ms":      round(elapsed_ms, 4),
        "pages_read":   pages_read,
        "file_size_kb": file_size_kb,
    })



@app.route("/api/delete", methods=["POST"])
def api_delete():
    data   = request.get_json(force=True)
    method = data.get("method", "sequential")
    engine, pager = _resolve(method)

    if engine is None:
        return jsonify({"error": f"Unknown method '{method}'"}), 400

    try:
        search_id = int(data["id"])
    except (KeyError, ValueError) as exc:
        return jsonify({"error": f"Bad input: {exc}"}), 400

    t0         = time.perf_counter()
    deleted    = engine.delete(search_id)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return jsonify({
        "success":  deleted,
        "method":   method,
        "time_ms":  round(elapsed_ms, 4),
    })



if __name__ == "__main__":
    print("\n🚀  DBMS Benchmark Server running at http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
