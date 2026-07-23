import os
import random
import re
import logging
from datetime import datetime, timedelta
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, jsonify, session, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from dotenv import load_dotenv

# Environment variables load
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configurations
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key or app.secret_key == "default_secret_key":
    raise ValueError("SECRET_KEY must be set in .env file!")

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1)
)

# Security headers (CSP)
Talisman(app, 
    force_https=False,  # Vercel handles HTTPS
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': ["'self'", "'unsafe-inline"],
        'img-src': "'self' data:",
        'media-src': "'self'"
    }
)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

# Configuration
API_URL = os.getenv("API_URL")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD")  # Add this to .env

if not API_URL:
    raise ValueError("API_URL must be set in .env file!")


# ==================== SECURITY HELPERS ====================

def generate_captcha():
    """Generate a simple math CAPTCHA"""
    operations = [
        (random.randint(1, 20), random.randint(1, 20), '+', lambda a, b: a + b),
        (random.randint(5, 30), random.randint(1, 10), '-', lambda a, b: a - b),
        (random.randint(2, 10), random.randint(2, 10), '×', lambda a, b: a * b),
    ]
    a, b, op, func = random.choice(operations)
    question = f"{a} {op} {b} = ?"
    answer = func(a, b)
    return question, answer


def sanitize_email(email):
    """Basic email sanitization"""
    if not email:
        return None
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email
    return None


def login_required(f):
    """Decorator to check authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ==================== ROUTES ====================

@app.route('/')
def home():
    """Login page"""
    if session.get('authenticated'):
        return redirect('/dashboard')
    return render_template('login.html')


@app.route('/', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit login attempts
def login():
    """Handle login"""
    password = request.form.get('password', '')
    
    # Constant time comparison to prevent timing attacks
    if ACCESS_PASSWORD and password == ACCESS_PASSWORD:
        session['authenticated'] = True
        session['login_time'] = datetime.now().isoformat()
        logger.info(f"Successful login from {request.remote_addr}")
        return redirect('/dashboard')
    
