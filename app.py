# app.py - الملف الكامل للموقع العقاري العالمي EverestProp
# ارفع هذا الملف فقط على GitHub ثم انشره على Render.com

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
import json
import os
import uuid

# ==================== إعدادات التطبيق ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'everestprop_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///everestprop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# إنشاء مجلد رفع الملفات
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==================== قاعدة البيانات ====================
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# جداول قاعدة البيانات
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    properties = db.relationship('Property', backref='owner', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    property_type = db.Column(db.String(20))
    transaction_type = db.Column(db.String(20))
    country = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(300))
    price = db.Column(db.Float, nullable=False)
    area = db.Column(db.Float)
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Integer)
    description = db.Column(db.Text)
    images = db.Column(db.Text)
    is_featured = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_images(self):
        return json.loads(self.images) if self.images else []
    
    def set_images(self, images_list):
        self.images = json.dumps(images_list)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== بياناتك الشخصية ====================
# حسابك البنكي بالجنيه المصري - البنك الأهلي المصري
BANK_IBAN = "EG20003041650001374988010160"
BANK_NAME = "البنك الأهلي المصري"

# PayPal
PAYPAL_EMAIL = "mohamedgabershalan@gmail.com"

# محفظة بيتكوين (BSC - BNB Smart Chain)
BITCOIN_ADDRESS = "0x93edbf8b70486a4c8a6d8a2b59ac304ecb90c3a9"

# نسبة عمولة السمسرة (1%)
COMMISSION_PERCENT = 1
MIN_COMMISSION_USD = 20

# ==================== كود الإعلانات ====================
# ضع كود Adsterra هنا بعد الحصول عليه
ADS_CODE = """
<!-- سيتم وضع كود Adsterra هنا لاحقاً -->
"""

# ==================== دوال مساعدة ====================
def get_usd_to_egp():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
        data = response.json()
        return data['rates'].get('EGP', 30.9)
    except:
        return 30.9

def get_prices():
    prices = {
        'gold_usd': 1920,
        'usd_egp': 30.9,
        'eur_egp': 33.5,
        'sar_egp': 8.25
    }
    try:
        # سعر الذهب
        gold_response = requests.get('https://api.gold-api.com/price/XAU', timeout=10)
        if gold_response.status_code == 200:
            prices['gold_usd'] = gold_response.json().get('price', 1920)
        
        # أسعار العملات
        forex_response = requests.get('https://api.exchangerate-api.com/v4/latest/EGP', timeout=10)
        if forex_response.status_code == 200:
            data = forex_response.json()
            prices['usd_egp'] = 1 / data['rates'].get('USD', 0.032) if data['rates'].get('USD') else 30.9
            prices['eur_egp'] = 1 / data['rates'].get('EUR', 0.029) if data['rates'].get('EUR') else 33.5
            prices['sar_egp'] = 1 / data['rates'].get('SAR', 0.12) if data['rates'].get('SAR') else 8.25
    except:
        pass
    return prices

# ==================== صفحات الموقع ====================
@app.route('/')
def index():
    prices = get_prices()
    usd_to_egp = prices['usd_egp']
    latest_properties = Property.query.order_by(Property.created_at.desc()).limit(9).all()
    featured_properties = Property.query.filter_by(is_featured=True).limit(6).all()
    
    for prop in latest_properties:
        prop.price_egp_display = prop.price * usd_to_egp
    for prop in featured_properties:
        prop.price_egp_display = prop.price * usd_to_egp
    
    return render_template_string(INDEX_HTML, prices=prices, latest_properties=latest_properties, 
                                  featured_properties=featured_properties, ads_code=ADS_CODE,
                                  current_user=current_user)

@app.route('/search')
def search():
    prices = get_prices()
    usd_to_egp = prices['usd_egp']
    query = Property.query
    
    country = request.args.get('country', '')
    city = request.args.get('city', '')
    property_type = request.args.get('type', '')
    transaction_type = request.args.get('transaction', '')
    
    if country:
        query = query.filter(Property.country.ilike(f'%{country}%'))
    if city:
        query = query.filter(Property.city.ilike(f'%{city}%'))
    if property_type:
        query = query.filter(Property.property_type == property_type)
    if transaction_type:
        query = query.filter(Property.transaction_type == transaction_type)
    
    properties = query.order_by(Property.created_at.desc()).all()
    for prop in properties:
        prop.price_egp_display = prop.price * usd_to_egp
    
    return render_template_string(SEARCH_HTML, properties=properties, prices=prices, 
                                  request_args=request.args, ads_code=ADS_CODE, current_user=current_user)

@app.route('/property/<int:property_id>')
def view_property(property_id):
    prices = get_prices()
    usd_to_egp = prices['usd_egp']
    property_item = Property.query.get_or_404(property_id)
    property_item.views += 1
    db.session.commit()
    property_item.price_egp_display = property_item.price * usd_to_egp
    
    similar = Property.query.filter(Property.country == property_item.country, 
                                     Property.id != property_item.id).limit(4).all()
    for sim in similar:
        sim.price_egp_display = sim.price * usd_to_egp
    
    seller = User.query.get(property_item.user_id) if property_item.user_id else None
    
    return render_template_string(PROPERTY_HTML, property=property_item, similar=similar, seller=seller,
                                  prices=prices, commission_percent=COMMISSION_PERCENT, min_commission=MIN_COMMISSION_USD,
                                  bank_iban=BANK_IBAN, bank_name=BANK_NAME, paypal_email=PAYPAL_EMAIL,
                                  bitcoin_address=BITCOIN_ADDRESS, ads_code=ADS_CODE, current_user=current_user)

@app.route('/add-property', methods=['GET', 'POST'])
@login_required
def add_property():
    prices = get_prices()
    
    if request.method == 'POST':
        title = request.form.get('title')
        property_type = request.form.get('property_type')
        transaction_type = request.form.get('transaction_type')
        country = request.form.get('country')
        city = request.form.get('city')
        address = request.form.get('address')
        price = float(request.form.get('price', 0))
        area = float(request.form.get('area', 0)) if request.form.get('area') else None
        bedrooms = int(request.form.get('bedrooms', 0)) if request.form.get('bedrooms') else None
        bathrooms = int(request.form.get('bathrooms', 0)) if request.form.get('bathrooms') else None
        description = request.form.get('description')
        contact_phone = request.form.get('contact_phone')
        contact_email = request.form.get('contact_email')
        
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    images.append(f'/static/uploads/{filename}')
        
        new_property = Property(
            title=title, property_type=property_type, transaction_type=transaction_type,
            country=country, city=city, address=address, price=price, area=area,
            bedrooms=bedrooms, bathrooms=bathrooms, description=description,
            contact_phone=contact_phone, contact_email=contact_email, user_id=current_user.id
        )
        new_property.set_images(images)
        db.session.add(new_property)
        db.session.commit()
        
        flash('تم إضافة العقار بنجاح!', 'success')
        return redirect(url_for('view_property', property_id=new_property.id))
    
    return render_template_string(ADD_PROPERTY_HTML, prices=prices, ads_code=ADS_CODE, current_user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    prices = get_prices()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        country = request.form.get('country')
        city = request.form.get('city')
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('اسم المستخدم أو البريد الإلكتروني موجود مسبقاً', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, phone=phone, country=country, city=city)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('تم إنشاء الحساب بنجاح!', 'success')
        return redirect(url_for('index'))
    
    return render_template_string(REGISTER_HTML, prices=prices, ads_code=ADS_CODE, current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    prices = get_prices()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'مرحباً {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template_string(LOGIN_HTML, prices=prices, ads_code=ADS_CODE, current_user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    prices = get_prices()
    usd_to_egp = prices['usd_egp']
    user_properties = Property.query.filter_by(user_id=current_user.id).all()
    for prop in user_properties:
        prop.price_egp_display = prop.price * usd_to_egp
    
    return render_template_string(DASHBOARD_HTML, properties=user_properties, prices=prices,
                                  ads_code=ADS_CODE, bank_iban=BANK_IBAN, paypal_email=PAYPAL_EMAIL,
                                  bitcoin_address=BITCOIN_ADDRESS, current_user=current_user)

@app.route('/delete-property/<int:property_id>')
@login_required
def delete_property(property_id):
    property_item = Property.query.get_or_404(property_id)
    if property_item.user_id != current_user.id:
        flash('لا يمكنك حذف عقار ليس ملكك', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(property_item)
    db.session.commit()
    flash('تم حذف العقار بنجاح', 'success')
    return redirect(url_for('dashboard'))

# ==================== إنشاء قاعدة البيانات عند التشغيل ====================
with app.app_context():
    db.create_all()

# ==================== قوالب HTML ====================
# الصفحة الرئيسية
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EverestProp - قمة العقارات العالمية</title>
    <meta name="description" content="منصة عقارية عالمية تربط بين البائعين والمشترين">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Tajawal', 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); box-shadow: 0 2px 20px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 1000; border-radius: 0 0 20px 20px; }
        .header-content { display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; flex-wrap: wrap; }
        .logo { font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .nav-links { display: flex; gap: 25px; align-items: center; flex-wrap: wrap; }
        .nav-links a { text-decoration: none; color: #555; font-weight: 500; transition: 0.3s; }
        .nav-links a:hover { color: #667eea; }
        .btn-add { background: linear-gradient(135deg, #667eea, #764ba2); color: white !important; padding: 8px 20px; border-radius: 25px; }
        .prices-bar { background: rgba(0,0,0,0.8); color: white; padding: 12px; border-radius: 50px; margin: 20px 0; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px; }
        .price-item { font-size: 14px; }
        .price-value { font-weight: bold; color: #ffd700; }
        .search-section { background: white; border-radius: 30px; padding: 40px; margin: 30px 0; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .search-form { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; }
        .search-input { padding: 15px 25px; border: 2px solid #e0e0e0; border-radius: 50px; font-size: 16px; flex: 1; min-width: 200px; }
        .search-input:focus { outline: none; border-color: #667eea; }
        .search-btn { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; padding: 15px 40px; border-radius: 50px; font-size: 16px; cursor: pointer; }
        .search-btn:hover { transform: scale(1.05); }
        .section-title { font-size: 32px; color: white; margin: 40px 0 20px; text-align: center; }
        .properties-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; margin: 30px 0; }
        .property-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: 0.3s; cursor: pointer; }
        .property-card:hover { transform: translateY(-10px); }
        .property-image { width: 100%; height: 220px; object-fit: cover; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-size: 50px; }
        .property-info { padding: 20px; }
        .property-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
        .property-price { color: #667eea; font-size: 22px; font-weight: bold; }
        .property-price-egp { color: #888; font-size: 14px; }
        .property-location { color: #777; font-size: 14px; margin: 10px 0; }
        .property-type { display: inline-block; background: #f0f0f0; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
        .ayah-section { background: rgba(255,255,255,0.95); border-radius: 20px; padding: 20px; text-align: center; margin: 40px 0; font-size: 20px; font-weight: bold; color: #2d6a4f; }
        .share-section { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 20px; padding: 30px; text-align: center; color: white; margin: 40px 0; }
        .share-btn { background: white; color: #f5576c; border: none; padding: 12px 30px; border-radius: 50px; font-size: 16px; margin-top: 15px; cursor: pointer; font-weight: bold; }
        .footer { background: #1a1a2e; color: white; text-align: center; padding: 30px; border-radius: 20px 20px 0 0; margin-top: 50px; }
        .flash-message { padding: 15px; border-radius: 10px; margin: 20px 0; text-align: center; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        @media (max-width: 768px) { .header-content { flex-direction: column; gap: 15px; } .section-title { font-size: 24px; } }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content container">
            <div class="logo">🏔️ EverestProp</div>
            <div class="nav-links">
                <a href="/">الرئيسية</a>
                <a href="/search">بحث</a>
                {% if current_user.is_authenticated %}
                    <a href="/dashboard">لوحة التحكم</a>
                    <a href="/add-property" class="btn-add">➕ إضافة عقار</a>
                    <a href="/logout">🚪 خروج</a>
                {% else %}
                    <a href="/login">دخول</a>
                    <a href="/register" class="btn-add">إنشاء حساب</a>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash-message {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        <div class="prices-bar">
            <span class="price-item">🥇 الذهب: <span class="price-value">${{ "%.0f"|format(prices.gold_usd) }}</span></span>
            <span class="price-item">💵 الدولار: <span class="price-value">{{ "%.2f"|format(prices.usd_egp) }}</span> ج.م</span>
            <span class="price-item">💶 اليورو: <span class="price-value">{{ "%.2f"|format(prices.eur_egp) }}</span> ج.م</span>
            <span class="price-item">🇸🇦 الريال: <span class="price-value">{{ "%.2f"|format(prices.sar_egp) }}</span> ج.م</span>
        </div>
        
        <div class="search-section">
            <form action="/search" method="get" class="search-form">
                <input type="text" name="country" placeholder="🌍 البلد" class="search-input">
                <input type="text" name="city" placeholder="🏙️ المدينة" class="search-input">
                <select name="type" class="search-input">
                    <option value="">الكل</option>
                    <option value="شقة">شقة</option>
                    <option value="أرض">أرض</option>
                    <option value="فيلا">فيلا</option>
                    <option value="محل">محل</option>
                </select>
                <select name="transaction" class="search-input">
                    <option value="">الكل</option>
                    <option value="بيع">بيع</option>
                    <option value="إيجار">إيجار</option>
                </select>
                <button type="submit" class="search-btn">🔍 ابحث</button>
            </form>
        </div>
        
        {% if featured_properties %}
        <h2 class="section-title">⭐ عقارات مميزة</h2>
        <div class="properties-grid">
            {% for prop in featured_properties %}
            <div class="property-card" onclick="location.href='/property/{{ prop.id }}'">
                <div class="property-image">{{ '🏠' if not prop.get_images() else '' }}</div>
                <div class="property-info">
                    <div class="property-title">{{ prop.title[:50] }}</div>
                    <div class="property-price">${{ "%.0f"|format(prop.price) }}</div>
                    <div class="property-price-egp">≈ {{ "%.0f"|format(prop.price_egp_display) }} ج.م</div>
                    <div class="property-location">📍 {{ prop.city }}, {{ prop.country }}</div>
                    <span class="property-type">{{ prop.property_type }} - {{ prop.transaction_type }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <h2 class="section-title">🆕 أحدث العقارات</h2>
        <div class="properties-grid">
            {% for prop in latest_properties %}
            <div class="property-card" onclick="location.href='/property/{{ prop.id }}'">
                <div class="property-image">{{ '🏠' if not prop.get_images() else '' }}</div>
                <div class="property-info">
                    <div class="property-title">{{ prop.title[:50] }}</div>
                    <div class="property-price">${{ "%.0f"|format(prop.price) }}</div>
                    <div class="property-price-egp">≈ {{ "%.0f"|format(prop.price_egp_display) }} ج.م</div>
                    <div class="property-location">📍 {{ prop.city }}, {{ prop.country }}</div>
                    <span class="property-type">{{ prop.property_type }} - {{ prop.transaction_type }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="ayah-section">
            ﴿ يَا أَيُّهَا الَّذِينَ آمَنُوا أَوْفُوا بِالْعُقُودِ ﴾ [المائدة: 1]
        </div>
        
        <div class="share-section">
            <h3>🎁 شارك الموقع ليصبح عقارك مميزاً مجاناً</h3>
            <button class="share-btn" onclick="navigator.share ? navigator.share({title:'EverestProp',url:location.origin}) : alert('انسخ الرابط: '+location.origin)">📢 شارك الآن</button>
        </div>
    </div>
    
    <div class="footer">
        <p>EverestProp - منصة عقارية عالمية</p>
        <small>الموقع وسيط فقط، ننصح بمراجعة الأوراق الرسمية</small>
    </div>
    {{ ads_code | safe }}
</body>
</html>
'''

# باقي القوالب (بنفس الأسلوب المبسط للاختصار)
SEARCH_HTML = '''
<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>بحث - EverestProp</title><style>''' + '''*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:1200px;margin:0 auto}.header{background:white;border-radius:20px;padding:15px 30px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}.logo{font-size:24px;font-weight:bold;color:#667eea}.nav-links a{text-decoration:none;color:#555;margin:0 10px}.btn-add{background:#667eea;color:white;padding:8px 20px;border-radius:25px}.properties-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}.property-card{background:white;border-radius:15px;padding:15px;cursor:pointer}.property-card:hover{transform:translateY(-5px)}.flash-message{padding:10px;border-radius:10px;margin:10px 0}.success{background:#d4edda;color:#155724}.prices-bar{background:rgba(0,0,0,0.8);color:white;padding:10px;border-radius:50px;margin-bottom:20px;display:flex;justify-content:space-around}.back-link{display:inline-block;margin-top:20px;color:white}</style></head><body><div class="container"><div class="header"><div class="logo">🏔️ EverestProp</div><div class="nav-links">''' + '''
<a href="/">الرئيسية</a>''' + '''
{% if current_user.is_authenticated %}<a href="/dashboard">لوحة التحكم</a><a href="/add-property" class="btn-add">إضافة عقار</a><a href="/logout">خروج</a>{% else %}<a href="/login">دخول</a><a href="/register" class="btn-add">إنشاء حساب</a>{% endif %}
</div></div>
<div class="prices-bar"><span>🥇 ${{ "%.0f"|format(prices.gold_usd) }}</span><span>💵 {{ "%.2f"|format(prices.usd_egp) }} ج.م</span><span>💶 {{ "%.2f"|format(prices.eur_egp) }} ج.م</span></div>
<h1 style="color:white">نتائج البحث</h1>
<div class="properties-grid">
{% for prop in properties %}
<div class="property-card" onclick="location.href='/property/{{ prop.id }}'">
<h3>{{ prop.title[:40] }}</h3>
<p>${{ "%.0f"|format(prop.price) }} (≈ {{ "%.0f"|format(prop.price_egp_display) }} ج.م)</p>
<p>📍 {{ prop.city }}, {{ prop.country }}</p>
<span>{{ prop.property_type }} - {{ prop.transaction_type }}</span>
</div>
{% else %}
<p style="color:white">لا توجد عقارات مطابقة للبحث</p>
{% endfor %}
</div>
<a href="/" class="back-link">← العودة للرئيسية</a>
</div>
<div class="footer" style="text-align:center;margin-top:40px;color:white"><small>EverestProp</small></div>
{{ ads_code | safe }}
</body></html>
'''

# تبسيط باقي القوالب للاختصار (يمكنك إضافة التفاصيل لاحقاً)
PROPERTY_HTML = '<!DOCTYPE html><html><head><title>تفاصيل العقار</title><style>body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:1000px;margin:0 auto;background:white;border-radius:20px;padding:30px}</style></head><body><div class="container"><h1>{{ property.title }}</h1><p><strong>السعر:</strong> ${{ "%.0f"|format(property.price) }} (≈ {{ "%.0f"|format(property.price_egp_display) }} ج.م)</p><p><strong>الموقع:</strong> {{ property.city }}, {{ property.country }}</p><p><strong>الوصف:</strong> {{ property.description }}</p><hr><h3>طريقة الدفع (عمولة السمسرة {{ commission_percent }}%):</h3><p>🏦 {{ bank_name }}<br>IBAN: {{ bank_iban }}</p><p>💳 PayPal: {{ paypal_email }}</p><p>₿ Bitcoin: {{ bitcoin_address }}</p><div class="ayah">﴿ وَأَوْفُوا بِالْعُقُودِ ﴾</div><a href="/">← العودة</a></div>{{ ads_code | safe }}</body></html>'
ADD_PROPERTY_HTML = '<!DOCTYPE html><html><head><title>إضافة عقار</title><style>body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:800px;margin:0 auto;background:white;border-radius:20px;padding:30px}input,select,textarea{width:100%;padding:10px;margin:10px 0;border-radius:10px;border:1px solid #ddd}button{background:#667eea;color:white;padding:15px;border:none;border-radius:10px;cursor:pointer}</style></head><body><div class="container"><h1>➕ إضافة عقار جديد</h1><form method="POST" enctype="multipart/form-data"><input type="text" name="title" placeholder="عنوان العقار" required><select name="property_type"><option value="شقة">شقة</option><option value="أرض">أرض</option><option value="فيلا">فيلا</option></select><select name="transaction_type"><option value="بيع">بيع</option><option value="إيجار">إيجار</option></select><input type="text" name="country" placeholder="البلد" required><input type="text" name="city" placeholder="المدينة" required><input type="number" name="price" placeholder="السعر بالدولار" required><input type="text" name="contact_phone" placeholder="رقم الهاتف"><input type="email" name="contact_email" placeholder="البريد الإلكتروني"><textarea name="description" placeholder="وصف العقار"></textarea><input type="file" name="images" multiple><button type="submit">إضافة العقار</button></form><a href="/">← العودة</a></div>{{ ads_code | safe }}</body></html>'
LOGIN_HTML = '<!DOCTYPE html><html><head><title>دخول</title><style>body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:400px;margin:0 auto;background:white;border-radius:20px;padding:30px}input{width:100%;padding:10px;margin:10px 0;border-radius:10px}button{background:#667eea;color:white;padding:10px;width:100%;border:none;border-radius:10px}</style></head><body><div class="container"><h1>تسجيل الدخول</h1><form method="POST"><input type="email" name="email" placeholder="البريد الإلكتروني" required><input type="password" name="password" placeholder="كلمة المرور" required><button type="submit">دخول</button></form><a href="/register">ليس لديك حساب؟ سجل الآن</a></div>{{ ads_code | safe }}</body></html>'
REGISTER_HTML = '<!DOCTYPE html><html><head><title>تسجيل</title><style>body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:400px;margin:0 auto;background:white;border-radius:20px;padding:30px}input{width:100%;padding:10px;margin:10px 0;border-radius:10px}button{background:#667eea;color:white;padding:10px;width:100%;border:none;border-radius:10px}</style></head><body><div class="container"><h1>إنشاء حساب</h1><form method="POST"><input type="text" name="username" placeholder="اسم المستخدم" required><input type="email" name="email" placeholder="البريد الإلكتروني" required><input type="password" name="password" placeholder="كلمة المرور" required><input type="text" name="phone" placeholder="رقم الهاتف"><input type="text" name="country" placeholder="البلد"><button type="submit">تسجيل</button></form><a href="/login">لديك حساب؟ سجل دخولك</a></div>{{ ads_code | safe }}</body></html>'
DASHBOARD_HTML = '<!DOCTYPE html><html><head><title>لوحة التحكم</title><style>body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}.container{max-width:1000px;margin:0 auto;background:white;border-radius:20px;padding:30px}.property-item{border:1px solid #ddd;padding:15px;margin:10px 0;border-radius:10px}.delete{color:red;text-decoration:none}</style></head><body><div class="container"><h1>لوحة التحكم</h1><h3>عقاراتي</h3>{% for prop in properties %}<div class="property-item"><strong>{{ prop.title }}</strong> - ${{ "%.0f"|format(prop.price) }}<br><a href="/property/{{ prop.id }}">عرض</a> | <a href="/delete-property/{{ prop.id }}" class="delete" onclick="return confirm(\'هل أنت متأكد?\')">حذف</a></div>{% else %}<p>لا توجد عقارات مضافة</p>{% endfor %}<a href="/add-property" class="btn-add" style="background:#667eea;color:white;padding:10px 20px;border-radius:25px;text-decoration:none">+ إضافة عقار جديد</a><br><br><a href="/">← العودة للرئيسية</a></div>{{ ads_code | safe }}</body></html>'

# ==================== تشغيل التطبيق ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
