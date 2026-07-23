import os
import random
import re
import json
from datetime import datetime, timedelta

import requests
from flask import Flask, render_template, request, redirect, jsonify, session

app = Flask(__name__)

# Secret key from environment
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key-change-in-production")
app.config['SESSION_TYPE'] = 'filesystem'

# Configuration
API_URL = os.getenv("API_URL", "https://sso-register-killersharmabot.vercel.app/send-email")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "admin123")

# In-memory storage for rate limiting (use Redis in production)
request_counts = {}

def generate_captcha():
    """Generate math CAPTCHA"""
    ops = [
        (random.randint(1, 20), random.randint(1, 20), '+'),
        (random.randint(5, 30), random.randint(1, 10), '-'),
        (random.randint(2, 10), random.randint(2, 10), '×'),
    ]
    a, b, op = random.choice(ops)
    if op == '+':
        ans = a + b
    elif op == '-':
        ans = a - b
    else:
        ans = a * b
    return f"{a} {op} {b} = ?", ans

def check_rate_limit(ip, action, limit=5, window=300):
    """Simple rate limiting"""
    key = f"{ip}:{action}"
    now = datetime.now().timestamp()
    
    if key not in request_counts:
        request_counts[key] = []
    
    # Remove old entries
    request_counts[key] = [t for t in request_counts[key] if now - t < window]
    
    if len(request_counts[key]) >= limit:
        return False
    
    request_counts[key].append(now)
    return True

@app.route('/')
def home():
    if session.get('authenticated'):
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/', methods=['POST'])
def login():
    password = request.form.get('password', '')
    ip = request.remote_addr
    
    if not check_rate_limit(ip, 'login'):
        return render_template('login.html', error="Too many attempts. Try again later."), 429
    
    if password == ACCESS_PASSWORD:
        session['authenticated'] = True
        return redirect('/dashboard')
    
    return render_template('login.html', error="Invalid password."), 401

@app.route('/dashboard')
def dashboard():
    if not session.get('authenticated'):
        return redirect('/')
    return render_template('index.html')

@app.route('/get-captcha')
def get_captcha():
    if not session.get('authenticated'):
        return jsonify({'status': 'error'}), 401
    
    question, answer = generate_captcha()
    session['captcha_result'] = answer
    session['captcha_time'] = datetime.now().isoformat()
    
    return jsonify({'status': 'success', 'question': question})

@app.route('/send-otp', methods=['POST'])
def send_otp():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    ip = request.remote_addr
    if not check_rate_limit(ip, 'otp', limit=3):
        return jsonify({'status': 'error', 'message': 'Too many requests'}), 429
    
    data = request.get_json() or {}
    email = data.get('email', '').lower().strip()
    user_captcha = str(data.get('captcha', '')).strip()
    
    # Email validation
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    # CAPTCHA check
    expected = session.get('captcha_result')
    if not expected or user_captcha != str(expected):
        return jsonify({'status': 'error', 'message': 'Incorrect CAPTCHA'}), 400
    
    session.pop('captcha_result', None)
    
    # Call API
    try:
        resp = requests.get(API_URL, params={'email': email}, timeout=10)
        data = resp.json()
        
        if resp.status_code == 200 and data.get('status_code') == 200:
            return jsonify({'status': 'success', 'message': 'OTP sent!'})
        return jsonify({'status': 'error', 'message': 'Failed to send OTP'}), 500
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Service error'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Vercel handler
def handler(event, context):
    from flask import Flask
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)
