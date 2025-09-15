from flask import Flask, request, render_template, redirect, url_for, session, flash
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import timedelta, datetime
from threading import Lock

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret")
app.permanent_session_lifetime = timedelta(days=1)

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


BATCH_SIZE = 50
attendance_cache = {}      
pending_attendance = []   
lock = Lock()              

def flush_pending():
    """Flush pending attendance records to Google Sheets."""
    global pending_attendance
    if not pending_attendance:
        return 0

    rows = [
        [r["Delegate_ID"], r["name"], r["committee"], r.get("portfolio", ""),
         r["scanned_by"], r["timestamp"]]
        for r in pending_attendance
    ]
    attendance_sheet.append_rows(rows)

    
    for r in pending_attendance:
        attendance_cache[r["Delegate_ID"]] = r

    flushed_count = len(pending_attendance)
    pending_attendance = []
    return flushed_count

def refresh_cache():
    """Reload attendance cache from Google Sheets."""
    global attendance_cache
    records = attendance_sheet.get_all_records()
    attendance_cache = {r["Delegate_ID"]: r for r in records}


@app.route("/")
def home():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    return render_template(
        "home.html",
        oc_id=session["oc_id"],
        delegate=None,
        delegate_id=None,
        pending_count=len(pending_attendance)
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        oc_id = request.form.get("oc_id")
        password = request.form.get("password")
        if oc_id in oc_list and oc_list[oc_id] == password:
            session.permanent = True
            session["oc_id"] = oc_id
            return redirect(url_for("home"))
        else:
            error = "Invalid Credentials"
    return render_template("Login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("oc_id", None)
    return redirect(url_for("login"))

@app.route("/scan/<delegate_id>")
def scan(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))
    oc_id = session["oc_id"]

    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} not found."
    delegate = delegates[delegate_id]

    cached_record = attendance_cache.get(delegate_id)
    scanned_delegate = {
        "name": delegate["name"],
        "country": delegate.get("country", ""),
        "committee": delegate["committee"],
        "portfolio": delegate.get("portfolio", ""),
        "liability_form": delegate.get("liability_form", ""),
        "transport_form": delegate.get("transport_form", ""),
        "scanned_by": cached_record.get("scanned_by") if cached_record else None,
        "timestamp": cached_record.get("timestamp") if cached_record else None
    }

    return render_template(
        "home.html",
        delegate=scanned_delegate,
        delegate_id=delegate_id,
        oc_id=oc_id,
        pending_count=len(pending_attendance)
    )

@app.route("/validate/<delegate_id>", methods=["POST"])
def validate(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))
    oc_id = session["oc_id"]

    with lock:
        
        if delegate_id in attendance_cache or any(r["Delegate_ID"] == delegate_id for r in pending_attendance):
            return redirect(url_for("scan", delegate_id=delegate_id))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        delegate = delegates.get(delegate_id, {})
        record = {
            "Delegate_ID": delegate_id,
            "name": delegate.get("name", ""),
            "committee": delegate.get("committee", ""),
            "portfolio": delegate.get("portfolio", ""),
            "scanned_by": oc_id,
            "timestamp": timestamp
        }

        
        attendance_cache[delegate_id] = record
        pending_attendance.append(record)

        if len(pending_attendance) >= BATCH_SIZE:
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
    flash(f"✅ Flushed {count} pending attendance records to Google Sheets.")
    return redirect(url_for("home"))

@app.route("/refresh_cache")
def refresh_route():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    refresh_cache()
    flash("🔄 Attendance cache refreshed from Google Sheets.")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=False)
