from flask import Flask, request, render_template, redirect, url_for, session, flash
import gspread
import os, json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import redis, time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret")
app.permanent_session_lifetime = timedelta(days=1)

redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True
)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

master_sheet = client.open("Master_Sheet").worksheet("Sheet1")
attendance_sheet = client.open("Attendance_Log").worksheet("Sheet1")
ocs_sheet = client.open("OC_Details").worksheet("Sheet1")

oc_list = {r["OC_ID"]: r["Password"] for r in ocs_sheet.get_all_records()}

delegates = {
    r["Delegate_ID"]: {
        "name": r["Name"],
        "country": r.get("Country", ""),
        "committee": r["Comittee"],
        "portfolio": r.get("Portfolio", ""),
        "liability_form": r.get("Liability_Form", ""),
        "transport_form": r.get("Transport_Form", "")
    }
    for r in master_sheet.get_all_records()
}

def flush_pending():
    rows = []
    while True:
        record_json = redis_client.lpop("pending_attendance")
        if not record_json:
            break
        r = json.loads(record_json)
        rows.append([
            r["Delegate_ID"], r["name"], r["committee"],
            r.get("portfolio",""), r["scanned_by"], r["timestamp"]
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

def auto_flush(interval=10):
    while True:
        time.sleep(interval)
        flush_pending()

@app.route("/")
def home():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", oc_id=session["oc_id"], delegate=None, delegate_id=None,
                           pending_count=redis_client.llen("pending_attendance"))

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method=="POST":
        oc_id = request.form.get("oc_id")
        password = request.form.get("password")
        if oc_id in oc_list and oc_list[oc_id]==password:
            session.permanent=True
            session["oc_id"]=oc_id
            return redirect(url_for("home"))
        else:
            error="Invalid Credentials"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("oc_id", None)
    return redirect(url_for("login"))

@app.route("/scan/<delegate_id>")
def scan(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))
    oc_id = session["oc_id"]
    delegate = delegates.get(delegate_id)
    if not delegate:
        return f"❌ Delegate {delegate_id} not found."
    cached_record_json = redis_client.hget("attendance_cache", delegate_id)
    cached_record = json.loads(cached_record_json) if cached_record_json else None
    scanned_delegate = {
        "name": delegate["name"],
        "country": delegate.get("country",""),
        "committee": delegate["committee"],
        "portfolio": delegate.get("portfolio",""),
        "liability_form": delegate.get("liability_form",""),
        "transport_form": delegate.get("transport_form",""),
        "scanned_by": cached_record["scanned_by"] if cached_record else None,
        "timestamp": cached_record["timestamp"] if cached_record else None
    }
    return render_template("home.html", delegate=scanned_delegate, delegate_id=delegate_id, oc_id=oc_id,
                           pending_count=redis_client.llen("pending_attendance"))

@app.route("/validate/<delegate_id>", methods=["POST"])
def validate(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))
    oc_id = session["oc_id"]
    if redis_client.hexists("attendance_cache", delegate_id) or \
       any(json.loads(r)["Delegate_ID"]==delegate_id for r in redis_client.lrange("pending_attendance",0,-1)):
        return redirect(url_for("scan", delegate_id=delegate_id))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    delegate = delegates[delegate_id]
    record = {
        "Delegate_ID": delegate_id,
        "name": delegate["name"],
        "committee": delegate["committee"],
        "portfolio": delegate.get("portfolio",""),
        "scanned_by": oc_id,
        "timestamp": timestamp
    }
    redis_client.rpush("pending_attendance", json.dumps(record))
    redis_client.hset("attendance_cache", delegate_id, json.dumps(record))
    if redis_client.llen("pending_attendance") >= 50:
        flush_pending()
    return redirect(url_for("scan", delegate_id=delegate_id))

@app.route("/manual_scan", methods=["POST"])
def manual_scan():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    delegate_id = request.form.get("delegate_id").strip()
    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} not found."
    return redirect(url_for("scan", delegate_id=delegate_id))

@app.route("/flush")
def flush_route():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    count = flush_pending()
    flash(f"✅ Pushed {count} pending attendance records to Google Sheets.")
    return redirect(url_for("home"))

@app.route("/refresh_cache")
def refresh_route():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    refresh_cache()
    flash("🔄 Attendance cache refreshed from Google Sheets.")
    return redirect(url_for("home"))

if __name__=="__main__":
    import threading
    thread = threading.Thread(target=auto_flush, args=(10,), daemon=True)
    thread.start()
    app.run(debug=False)
