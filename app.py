import os
import random
import requests
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
# সেশনের নিরাপত্তার জন্য একটি সিক্রেট কি দেওয়া হলো
app.secret_key = "my-custom-secret-key-change-this"

# আপনার API URL সরাসরি নিচে বসিয়ে দিন
API_URL = "https://sso-register-killersharmabot.vercel.app/send-email"

def generate_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return f"{a} + {b} = ?", a + b

@app.route('/')
@app.route('/dashboard')
def home():
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
    captcha_user = str(data.get('captcha', '')).strip()
    captcha_real = str(session.get('captcha_result', ''))

    if not email or not captcha_user:
        return jsonify({'status': 'error', 'message': 'সবগুলো ঘর পূরণ করুন!'})

    if captcha_user != captcha_real:
        return jsonify({'status': 'error', 'message': 'ক্যাপচা ভুল হয়েছে!'})

    try:
        response = requests.post(API_URL, json={'email': email}, timeout=10)
        q, a = generate_captcha()
        session['captcha_result'] = a

        if response.status_code == 200:
            return jsonify({
                'status': 'success',
                'message': 'কোডটি সফলভাবে পাঠানো হয়েছে! এই কোডটি দিয়ে আপনি আপনার অ্যাকাউন্ট রিকভারি বা অন্য কাজ করতে পারবেন।',
                'new_question': q
            })
        else:
            return jsonify({'status': 'error', 'message': 'API রিকোয়েস্ট ব্যর্থ হয়েছে।', 'new_question': q})
    except Exception as e:
        q, a = generate_captcha()
        session['captcha_result'] = a
        return jsonify({'status': 'error', 'message': 'সার্ভার কানেকশন এরর!', 'new_question': q})

if __name__ == '__main__':
    app.run(debug=True)
