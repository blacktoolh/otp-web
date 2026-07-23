import os
import random
import re
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, jsonify, session
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this")

# Config
API_URL = os.getenv("API_URL")
ACCESS_HASH = os.getenv("ACCESS_PASSWORD")  # এখানে হ্যাশ থাকবে
request_log = {}

def generate_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return f"{a} + {b} = ?", a + b

def rate_limit(ip, limit=5):
    now = datetime.now().timestamp()
    request_log[ip] = [t for t in request_log.get(ip, []) if now - t < 300]
    if len(request_log[ip]) >= limit:
        return False
    request_log[ip].append(now)
    return True

@app.route('/')
def home():
    if session.get('authenticated'):
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/', methods=['POST'])
def login():
    if not rate_limit(request.remote_addr):
        return render_template('login.html', error="Too many attempts!"), 429
    
    if check_password_hash(ACCESS_HASH, request.form.get('password', '')):
        session['authenticated'] = True
        return redirect('/dashboard')
    return render_template('login.html', error="Wrong password!"), 401

@app.route('/dashboard')
def dashboard():
    if not session.get('authenticated'):
        return redirect('/')
    return render_template('index.html')

@app.route('/get-captcha')
def get_captcha():
    if not session.get('authenticated'):
        return jsonify({'status': 'error'}), 401
    q, a = generate_captcha()
    session['captcha_result'] = a
    return jsonify({'status': 'success', 'question': q})

@app.route('/send-otp', methods=['POST'])
def send_otp():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    captcha = str(data.get('captcha', '')).strip()
    
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return jsonify({'status': 'error', 'message': 'Invalid email'}), 400
    
    if captcha != str(session.get('captcha_result', '')):
        return jsonify({'status': 'error', 'message': 'Wrong captcha'}), 400
    
    session.pop('captcha_result', None)
    
    try:
        r = requests.get(API_URL, params={'email': email}, timeout=10)
        if r.status_code == 200 and r.json().get('status_code') == 200:
            return jsonify({'status': 'success', 'message': 'OTP sent!'})
        return jsonify({'status': 'error', 'message': 'API error'}), 500
    except:
        return jsonify({'status': 'error', 'message': 'Request failed'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
