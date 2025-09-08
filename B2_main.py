from flask import Flask, request, render_template, redirect, url_for, session
import json, time
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "MUN2025"
app.permanent_session_lifetime = timedelta(days=1)

# Load OC credentials and delegate list
with open("oc_list.json") as f:
    oc_list = json.load(f)

with open("delegates.json") as f:
    delegates = json.load(f)

attendance_log = {}

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

    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} not found."

    delegate = delegates[delegate_id]

    scanned_delegate = {
        "name": delegate["name"],
        "country": delegate["country"],
        "committee": delegate["committee"],
        "liability_form": delegate["liability_form"],
        "transport_form": delegate["transport_form"],
        "scanned_by": None,
        "timestamp": None
    }

    if delegate_id in attendance_log:
        log = attendance_log[delegate_id]
        scanned_delegate["scanned_by"] = log["scanned by"]
        scanned_delegate["timestamp"] = log["timestamp"]

    return render_template(
        "home.html",
        oc_id=oc_id,
        delegate=scanned_delegate,
        delegate_id=delegate_id
    )

@app.route("/validate/<delegate_id>", methods=["POST"])
def validate(delegate_id):
    if "oc_id" not in session:
        return redirect(url_for("login"))

    oc_id = session["oc_id"]

    if delegate_id not in delegates:
        return f"❌ Delegate {delegate_id} does not exist"

    if delegate_id not in attendance_log:
        attendance_log[delegate_id] = {
            "scanned by": oc_id,
            "timestamp": time.ctime()
        }

    return redirect(url_for("scan", delegate_id=delegate_id))

if __name__ == "__main__":
    app.run(debug=True)