import os
import random
import re

import requests
from flask import Flask, render_template, request, redirect, jsonify, session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this")

API_URL = os.getenv("API_URL")

def generate_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return f"{a} + {b} = ?", a + b

# হোম পেজে ঢুকলেই সরাসরি ড্যাশবোর্ডে পাঠিয়ে দেবে
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('index.html')

@app.route('/get-captcha')
def get_captcha():
    q, a = generate_captcha()
    session['captcha_result'] = a
    return jsonify({'status': 'success', 'question': q})

@app.route('/send-otp', methods=['POST'])
def send_otp():
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
