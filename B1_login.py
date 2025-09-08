from flask import Flask, request, render_template, redirect, session
import json
app = Flask(__name__)
app.secret_key = 'MUN2025'

with open('oc_list.json') as f:
    oc_list = json.load(f)
    @app.route('/')
    def home():
        if 'oc_id' in session:
            return render_template('home.html', oc_id=session['oc_id'])
        return render_template('Login.html')
    @app.route('/login', methods=['POST'])
    def login():
        oc_id = request.form['oc_id']
        password = request.form['password']
        if oc_id in oc_list and oc_list[oc_id] == password:
            session['oc_id'] = oc_id
            return redirect('/scan')
        else:
            return "Invalid credentials, please try again"
    @app.route('/logout')
    def logout():
        session.pop('oc_id', None)
        return redirect('/')
if __name__ == '__main__':
    app.run(debug=True)