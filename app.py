import os
import random
import re
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, jsonify, session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this")

API_URL = os.getenv("API_URL")
# সরাসরি প্লেইন টেক্সট পাসওয়ার্ড নেওয়া হচ্ছে
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "fdsacXDvgfc54<>")

# ভুল পাসওয়ার্ড ট্রাই ট্র্যাক করার জন্য
failed_attempts = {}

def generate_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return f"{a} + {b} = ?", a + b

@app.route('/')
def home():
    if session.get('authenticated'):
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/', methods=['POST'])
def login():
    ip = request.remote_addr
    attempts = failed_attempts.get(ip, 0)
    
    # ৩ বারের বেশি চেষ্টা করলে ব্লক
    if attempts >= 3:
        return render_template('login.html', error="Maximum 3 attempts reached! You are blocked."), 429
    
    user_password = request.form.get('password')
    
    # সাধারণ টেক্সট ম্যাচিং
    if user_password == ACCESS_PASSWORD:
        session['authenticated'] = True
        failed_attempts[ip] = 0  # সফল হলে কাউন্টার রিসেট
        return redirect('/dashboard')
    else:
        failed_attempts[ip] = attempts + 1
        remaining = 3 - failed_attempts[ip]
        if remaining > 0:
            error_msg = f"Wrong password! Remaining attempts: {remaining}"
        else:
            error_msg = "Maximum 3 attempts reached! You are blocked."
        return render_template('login.html', error=error_msg), 401

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
