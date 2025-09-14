from flask import Flask, request, render_template, redirect, url_for, session
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import timedelta, datetime

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

# --- CACHE VARIABLES ---
master_sheet = client.open("Master_Sheet").worksheet("Sheet1")
attendance_sheet = client.open("Attendance_Log").worksheet("Sheet1")
ocs_sheet = client.open("OC_Details").worksheet("Sheet1")

delegates = {}
oc_list = {}
attendance_records = []

def refresh_cache():
    global delegates, oc_list, attendance_records
    delegates = {r["Delegate_ID"]: r for r in master_sheet.get_all_records()}
    oc_list = {r["OC_ID"]: r["Password"] for r in ocs_sheet.get_all_records()}
    attendance_records = attendance_sheet.get_all_records()

# Initial cache load
refresh_cache()

@app.route("/")
def home():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", oc_id=session["oc_id"], delegate=None, delegate_id=None)

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

    scanned_delegate = {
        "name": delegate["Name"],
        "country": delegate.get("Country", ""),
        "committee": delegate["Comittee"],
        "portfolio": delegate.get("Portfolio", ""),
        "liability_form": delegate.get("Liability_Form", ""),
        "transport_form": delegate.get("Transport_Form", ""),
        "scanned_by": None,
        "timestamp": None
    }

    for record in attendance_records:
        if record["Delegate_ID"] == delegate_id:
            scanned_delegate["scanned_by"] = record["OC_ID"]
            scanned_delegate["timestamp"] = record["Timestamp"]
            break

    return render_template("home.html", delegate=scanned_delegate, delegate_id=delegate_id, oc_id=oc_id)

@app.route("/validate/<delegate_id>", methods=["POST"])
def validate(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))
    oc_id = session["oc_id"]

    if not any(r["Delegate_ID"] == delegate_id for r in attendance_records):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        delegate = delegates.get(delegate_id, {})
        row = [
            delegate_id,
            delegate.get("Name", ""),
            delegate.get("Comittee", ""),
            delegate.get("Portfolio", ""),
            oc_id,
            timestamp
        ]
        attendance_records.append({
            "Delegate_ID": delegate_id,
            "Name": delegate.get("Name", ""),
            "Comittee": delegate.get("Comittee", ""),
            "Portfolio": delegate.get("Portfolio", ""),
            "OC_ID": oc_id,
            "Timestamp": timestamp
        })
        attendance_sheet.append_row(row)

    return redirect(url_for("scan", delegate_id=delegate_id))

@app.route("/manual_scan", methods=["POST"])
def manual_scan():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    delegate_id = request.form.get("delegate_id").strip()
    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} not found."
    return redirect(url_for("scan", delegate_id=delegate_id))

@app.route("/refresh_cache")
def refresh_cache_route():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    refresh_cache()
    return "✅ Cache refreshed!"

if __name__ == "__main__":
    app.run(debug=True)
