import os
import random
import requests
from flask import Flask, render_template, request, redirect, jsonify, session
from werkzeug.security import import_string
from dotenv import load_dotenv

# .env ফাইল লোড করা
load_dotenv()

app = Flask(__name__)

# Secret Key এবং API URL সেট করা
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
API_URL = os.getenv("API_URL")

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.json or {}
    email = data.get('email')
    user_captcha = data.get('captcha')

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    expected_captcha = session.get('captcha_result')
    if expected_captcha is None or str(user_captcha).strip() != str(expected_captcha):
        return jsonify({'status': 'error', 'message': 'Incorrect CAPTCHA answer'}), 400

    session.pop('captcha_result', None)

    api_url = os.getenv('API_URL')
    params = {'email': email}

    try:
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get('status_code') == 200:
                return jsonify({'status': 'success', 'message': 'OTP has been sent to your email!'})
            else:
                return jsonify({'status': 'error', 'message': f"API Error: {res_data}"})
        else:
            return jsonify({'status': 'error', 'message': f'Server Error: Status {response.status_code}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Request failed. Please try again.'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

