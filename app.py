from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import threading
import os
import json
import pandas as pd

app = Flask(__name__)

log_buffer = []
log_lock = threading.Lock()
running_task = {"status": "idle"}  # idle | running | done | error


def stream_log(line: str):
    with log_lock:
        log_buffer.append(line)


def run_script(script: str, env_overrides: dict = None):
    global log_buffer, running_task
    with log_lock:
        log_buffer = []
    running_task["status"] = "running"

    import os, sys
    env = os.environ.copy()
    if env_overrides:
        env.update({k: str(v) for k, v in env_overrides.items()})

    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )
        for line in proc.stdout:
            stream_log(line.rstrip())
        proc.wait()
        running_task["status"] = "done" if proc.returncode == 0 else "error"
    except Exception as e:
        stream_log(f"[ERROR] {e}")
        running_task["status"] = "error"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run_screener", methods=["POST"])
def api_run_screener():
    if running_task["status"] == "running":
        return jsonify({"error": "任務進行中"}), 409
    data = request.json or {}
    # 寫入臨時 config override
    overrides = {
        "MIN_GROSS_MARGIN": data.get("min_gross_margin", 0.30),
        "MIN_IC_GROWTH": data.get("min_ic_growth", 0.0),
        "ROIC_WACC_SPREAD": data.get("roic_wacc_spread", 0.0),
        "FINMIND_TOKEN": data.get("finmind_token", ""),
    }
    t = threading.Thread(target=run_script, args=("screener.py", overrides), daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/run_demo", methods=["POST"])
def api_run_demo():
    if running_task["status"] == "running":
        return jsonify({"error": "任務進行中"}), 409
    t = threading.Thread(target=run_script, args=("demo_backtest.py",), daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/run_backtest", methods=["POST"])
def api_run_backtest():
    if running_task["status"] == "running":
        return jsonify({"error": "任務進行中"}), 409
    t = threading.Thread(target=run_script, args=("backtest.py",), daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/logs")
def api_logs():
    with log_lock:
        logs = list(log_buffer)
    return jsonify({"logs": logs, "status": running_task["status"]})


@app.route("/api/results")
def api_results():
    files = {
        "selected": "output/selected_stocks.csv",
        "backtest": "output/backtest_result.csv",
        "demo": "output/demo_backtest_result.csv",
    }
    result = {}
    for key, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            result[key] = df.to_dict(orient="records")
        else:
            result[key] = []
    return jsonify(result)


@app.route("/api/chart/<name>")
def api_chart(name):
    allowed = {"backtest": "output/backtest_chart.png", "demo": "output/demo_backtest_chart.png"}
    path = allowed.get(name)
    if path and os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "", 404


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(debug=True, port=5000)
