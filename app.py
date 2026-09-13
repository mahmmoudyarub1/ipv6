from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import ipaddress

app = Flask(__name__)
app.config['SECRET_KEY'] = 'luxe_isp_secure_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///network_inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# جدول المستخدمين
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# جدول بيانات الشبكة والمنافذ والـ IPv6
class NetworkRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False) # مثل L6730
    interface_name = db.Column(db.String(50), nullable=True) # مثل Ethernet26/1
    vlan_id = db.Column(db.String(20), nullable=True) # مثل VLAN 51
    subnet = db.Column(db.String(100), nullable=False) # مثل 2a0a:4347:8888:8845::/64
    domain = db.Column(db.String(150), nullable=False) # مثل L6730.ipv6.luxeisp.com
    next_hop = db.Column(db.String(100), nullable=True) # مثل 2a0a:4340::1
    description = db.Column(db.String(255), nullable=True) # مثل PPPOE-SERVER

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# إنشاء الداتابيز وإنشاء حساب الأدمن الافتراضي إذا لم يكن موجوداً
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123', method='scrypt')
        admin_user = User(username='admin', password_hash=hashed_pw)
        db.session.add(admin_user)
        db.session.commit()

HTML_LAYOUT = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>لوحة إدارة وتوثيق شبكة LuxeISP</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h3 { color: #38bdf8; margin-top: 0; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px; }
        input, button, select { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; grid-column: span 1; }
        button:hover { background: #0369a1; }
        .danger-btn { background: #ef4444; padding: 6px 12px; }
        .danger-btn:hover { background: #dc2626; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #334155; padding: 10px; text-align: right; }
        th { background: #334155; color: #38bdf8; }
        .tag { background: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .code { font-family: monospace; color: #4ade80; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 20px; }
        .logout-link { color: #ef4444; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        {% if current_user.is_authenticated %}
        <div class="header-bar">
            <h1>نظام إدارة الشبكة والتناظرات (Network Inventory)</h1>
            <div>
                أهلاً بك، <strong>{{ current_user.username }}</strong> | 
                <a href="/logout" class="logout-link">تسجيل الخروج</a>
            </div>
        </div>

        <div class="card">
            <h3>1. استخراج أول IPv6 Subnet فارغ تلقائياً</h3>
            <form method="POST" action="/suggest" style="display: flex; gap: 10px;">
                <input type="text" name="parent" placeholder="الرينج الرئيسي (مثال: 2a0a:4340::/32)" required style="flex: 2;">
                <input type="number" name="prefixlen" value="48" placeholder="التقسيم (48 أو 64)" required style="flex: 1;">
                <button type="submit">حساب العنوان الفارغ</button>
            </form>
            {% if suggested %}
            <p style="margin-top: 10px;">العنوان المقترح التالي: <span class="code">{{ suggested }}</span></p>
            {% endif %}
        </div>

        <div class="card">
            <h3>2. إضافة وتوثيق Interface / Route / Domain</h3>
            <form method="POST" action="/add">
                <div class="form-grid">
                    <input type="text" name="code" placeholder="المعرف (مثال: L6730)" required>
                    <input type="text" name="interface_name" placeholder="Interface (مثال: Ethernet26/1)">
                    <input type="text" name="vlan_id" placeholder="VLAN (مثال: VLAN 51)">
                    <input type="text" name="subnet" placeholder="IPv6 Prefix" value="{{ suggested if suggested else '' }}" class="code" required>
                    <input type="text" name="domain" placeholder="الدومين الصوري (L6730.ipv6.luxeisp.com)" required>
                    <input type="text" name="next_hop" placeholder="Next Hop (مثال: 2a0a:4340::1)">
                    <input type="text" name="description" placeholder="الوصف (مثال: PPPOE-SERVER)">
                </div>
                <button type="submit" style="margin-top: 15px; width: 100%;">حفظ في قاعدة البيانات</button>
            </form>
        </div>

        <div class="card">
            <h3>جدول توثيق الشبكة والداتا المربوطة</h3>
            <table>
                <tr>
                    <th>المعرف</th>
                    <th>المنفذ (Interface)</th>
                    <th>VLAN</th>
                    <th>IPv6 Prefix</th>
                    <th>الدومين الإداري</th>
                    <th>Next-Hop</th>
                    <th>الوصف والوجهة</th>
                    <th>حذف</th>
                </tr>
                {% for r in records %}
                <tr>
                    <td><span class="tag">{{ r.code }}</span></td>
                    <td class="code">{{ r.interface_name or '-' }}</td>
                    <td>{{ r.vlan_id or '-' }}</td>
                    <td class="code">{{ r.subnet }}</td>
                    <td style="color:#38bdf8;">{{ r.domain }}</td>
                    <td class="code">{{ r.next_hop or '-' }}</td>
                    <td>{{ r.description or '-' }}</td>
                    <td><a href="/delete/{{ r.id }}"><button class="danger-btn">حذف</button></a></td>
                </tr>
                {% else %}
                <tr><td colspan="8" style="text-align:center;">لا توجد بيانات موثقة حالياً.</td></tr>
                {% endfor %}
            </table>
        </div>
        {% else %}
        <!-- صفحة تسجيل الدخول -->
        <div style="max-width: 400px; margin: 80px auto;" class="card">
            <h2 style="text-align: center; color: #38bdf8;">تسجيل الدخول للنظام</h2>
            {% if error %}
            <p style="color: #ef4444; text-align: center;">{{ error }}</p>
            {% endif %}
            <form method="POST" action="/login">
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <input type="text" name="username" placeholder="اسم المستخدم" required>
                    <input type="password" name="password" placeholder="كلمة المرور" required>
                    <button type="submit">دخول</button>
                </div>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template_string(HTML_LAYOUT)
    records = NetworkRecord.query.all()
    return render_template_string(HTML_LAYOUT, records=records)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect(url_for('index'))
    return render_template_string(HTML_LAYOUT, error="اسم المستخدم أو كلمة المرور غير صحيحة")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/suggest', methods=['POST'])
@login_required
def suggest():
    parent_str = request.form.get('parent')
    prefixlen = int(request.form.get('prefixlen'))
    records = NetworkRecord.query.all()
    
    try:
        parent_net = ipaddress.IPv6Network(parent_str, strict=False)
        used_nets = [ipaddress.IPv6Network(r.subnet, strict=False) for r in records]
        
        suggested = None
        for sub in parent_net.subnets(new_prefix=prefixlen):
            if not any(sub.overlaps(u) for u in used_nets):
                suggested = str(sub)
                break
                
        return render_template_string(HTML_LAYOUT, records=records, suggested=suggested)
    except Exception as e:
        return f"خطأ في تنسيق IPv6: {str(e)}", 400

@app.route('/add', methods=['POST'])
@login_required
def add():
    new_rec = NetworkRecord(
        code=request.form.get('code'),
        interface_name=request.form.get('interface_name'),
        vlan_id=request.form.get('vlan_id'),
        subnet=request.form.get('subnet'),
        domain=request.form.get('domain'),
        next_hop=request.form.get('next_hop'),
        description=request.form.get('description')
    )
    db.session.add(new_rec)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    rec = NetworkRecord.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8787)
