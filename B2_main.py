from flask import Flask, request, render_template, redirect, url_for, session
import gspread
from google.oauth2.service_account import Credentials
from datetime import timedelta, datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_fallback_secret")
app.permanent_session_lifetime = timedelta(days=1)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "secret_key.json",
    scopes=SCOPE
)
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
    records = attendance_sheet.get_all_records()
    scanned_delegate = {
        "name": delegate["name"],
        "country": delegate.get("country", ""),
        "committee": delegate["committee"],
        "portfolio": delegate.get("portfolio", ""),
        "liability_form": delegate.get("liability_form", ""),
        "transport_form": delegate.get("transport_form", ""),
        "scanned_by": None,
        "timestamp": None
    }
    for record in records:
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
    records = attendance_sheet.get_all_records()
    if not any(r["Delegate_ID"] == delegate_id for r in records):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        delegate = delegates.get(delegate_id, {})
        attendance_sheet.append_row([
            delegate_id,
            delegate.get("name", ""),
            delegate.get("committee", ""),
            delegate.get("portfolio", ""),
            oc_id,
            timestamp
        ])
    return redirect(url_for("scan", delegate_id=delegate_id))

@app.route("/manual_scan", methods=["POST"])
def manual_scan():
    if "oc_id" not in session:
        return redirect(url_for("login"))
    delegate_id = request.form.get("delegate_id").strip()
    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} not found."
    return redirect(url_for("scan", delegate_id=delegate_id))

if __name__ == "__main__":
    app.run(debug=True)
