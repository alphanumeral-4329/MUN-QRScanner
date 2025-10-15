import os
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify, render_template_string
import gspread, json, redis
from google.oauth2.service_account import Credentials
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret")

redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "red-d3joasmr433s739fqv00"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True
)

SCOPE = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

master_sheet = client.open("Master_Sheet").worksheet("Sheet1")
attendance_sheet = client.open("Attendance_Log").worksheet("Sheet1")
ocs_sheet = client.open("OC_Details").worksheet("Sheet1")

oc_list = {str(r["OC_ID"]).strip(): r["Password"].strip() for r in ocs_sheet.get_all_records()}

delegates = {
    str(r["Delegate_ID"]).strip(): {
        "name": r["Name"],
        "committee": r["Committee"],
        "portfolio": r.get("Portfolio", ""),
        "liability_form": r.get("Liability_Form", ""),
        "transport_form": r.get("Transport_Form", "")
    }
    for r in master_sheet.get_all_records()
}

DEBUG_MODE = os.environ.get("DEBUG_MODE", "False") == "True"

def flush_pending():
    rows = []
    while True:
        record_json = redis_client.lpop("pending_attendance")
        if not record_json:
            break
        r = json.loads(record_json)
        rows.append([
            str(r["Delegate_ID"]).strip(),
            r["name"],
            r["committee"],
            r.get("portfolio", ""),
            str(r["scanned_by"]).strip(),
            r["timestamp"]
        ])
    if rows:
        attendance_sheet.append_rows(rows)
        for r in rows:
            redis_client.hset("attendance_cache", r[0], json.dumps({
                "Delegate_ID": r[0],
                "name": r[1],
                "committee": r[2],
                "portfolio": r[3],
                "scanned_by": r[4],
                "timestamp": r[5]
            }))
    return len(rows)

def refresh_cache():
    records = attendance_sheet.get_all_records()
    redis_client.delete("attendance_cache")
    for r in records:
        redis_client.hset("attendance_cache", r["Delegate_ID"], json.dumps(r))

@app.route("/")
def home():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", oc_id=session["oc_id"], delegate=None, delegate_id=None)

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        oc_id = request.form.get("oc_id")
        password = request.form.get("password")
        if oc_id in oc_list and oc_list[oc_id] == password:
            session.permanent = True
            session["oc_id"] = oc_id
            session["scan_count"] = 0
            return redirect(url_for("home"))
        else:
            error = "Invalid Credentials"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("oc_id", None)
    session.pop("scan_count", None)
    return redirect(url_for("login"))

@app.route("/scan/<delegate_id>")
def scan(delegate_id):
    if "oc_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    session["scan_count"] = session.get("scan_count", 0) + 1
    oc_id = session["oc_id"]
    delegate = delegates.get(delegate_id)
    if not delegate:
        return jsonify({"error": f"Delegate {delegate_id} not found"}), 404

    cached_record_json = redis_client.hget("attendance_cache", delegate_id)
    cached_record = json.loads(cached_record_json) if cached_record_json else None
    status = "already" if cached_record else "success"

    scanned_delegate = {
        "name": delegate["name"],
        "committee": delegate["committee"],
        "portfolio": delegate.get("portfolio", ""),
        "liability_form": delegate.get("liability_form", ""),
        "transport_form": delegate.get("transport_form", ""),
        "scanned_by": cached_record["scanned_by"] if cached_record else oc_id,
        "timestamp": cached_record["timestamp"] if cached_record else datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    }

    if not cached_record:
        record = {
            "Delegate_ID": delegate_id,
            "name": delegate["name"],
            "committee": delegate["committee"],
            "portfolio": delegate.get("portfolio", ""),
            "scanned_by": oc_id,
            "timestamp": scanned_delegate["timestamp"]
        }
        redis_client.rpush("pending_attendance", json.dumps(record))
        redis_client.hset("attendance_cache", delegate_id, json.dumps(record))
        if redis_client.llen("pending_attendance") >= 50:
            flush_pending()

    delegate_html = render_template_string("""
    <div class="delegate-card">
        <span class="oc-id">Logged in as: {{ oc_id }}</span>
        <div class="card-buttons">
            <a href="{{ url_for('refresh_route') }}" class="btn">Refresh Cache</a>
            <a href="{{ url_for('logout') }}" class="btn">Logout</a>
        </div>
        <h2>{{ delegate.name }} ({{ delegate_id }})</h2>
        <p>Committee: {{ delegate.committee }}</p>
        <p>Portfolio: {{ delegate.portfolio }}</p>
        <p>Liability Form: {{ delegate.liability_form }}</p>
        <p>Transport Form: {{ delegate.transport_form }}</p>
        {% if delegate.status == 'already' %}
            <p class="scanned">✅ Already scanned by {{ delegate.scanned_by }} at {{ delegate.timestamp }}</p>
        {% else %}
            <p class="scanned">✅ New scan recorded by {{ delegate.scanned_by }} at {{ delegate.timestamp }}</p>
        {% endif %}
    </div>
    """, delegate=scanned_delegate, delegate_id=delegate_id, oc_id=oc_id)

    message = "Already scanned" if cached_record else "Scan successful"
    success = not cached_record

    return jsonify({"delegateHTML": delegate_html, "message": message, "success": success, "scan_count": session["scan_count"]})

@app.route("/refresh_cache")
def refresh_route():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    refresh_cache()
    flash("🔄 Attendance cache refreshed from Google Sheets.")
    return redirect(url_for("home"))

if DEBUG_MODE:
    @app.route("/debug/redis")
    def debug_redis():
        if "oc_id" not in session:
            return "Not logged in", 401
        total_keys = redis_client.dbsize()
        cache_count = redis_client.hlen("attendance_cache")
        pending_count = redis_client.llen("pending_attendance")
        scan_count = session.get("scan_count", 0)
        return (
            f"Total keys in Redis: {total_keys}<br>"
            f"Delegates in attendance_cache: {cache_count}<br>"
            f"Pending attendance records: {pending_count}<br>"
            f"Your session scan_count: {scan_count}"
        )

    @app.route("/flush_cache")
    def flush_cache_route():
        if "oc_id" not in session:
            return "Not logged in", 401

        
        redis_client.delete("attendance_cache")

        
        session.pop("scan_count", None)

        return "✅ attendance_cache and scan_count cleared successfully."

if __name__ == "__main__":
    app.run(debug=False)
