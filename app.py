from flask import Flask, request, render_template_string, redirect, url_for
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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# جدول الرينجات الأصلية (Parent Pools)
class ParentPool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)

# جدول الرينجات المستقطعة والربط
class NetworkRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    interface_name = db.Column(db.String(50), nullable=True)
    vlan_id = db.Column(db.String(20), nullable=True)
    subnet = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(150), nullable=False)
    next_hop = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(255), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    <title>إدارة شبكة LuxeISP وكتل IPv6</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }
        .container { max-width: 1350px; margin: 0 auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h3 { color: #38bdf8; margin-top: 0; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-top: 10px; }
        input, button, select { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; }
        button:hover { background: #0369a1; }
        .action-btn { background: #10b981; padding: 5px 10px; font-size: 12px; }
        .action-btn:hover { background: #059669; }
        .danger-btn { background: #ef4444; padding: 6px 12px; }
        .danger-btn:hover { background: #dc2626; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #334155; padding: 10px; text-align: right; }
        th { background: #334155; color: #38bdf8; }
        .tag { background: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .status-ok { background: #166534; color: #4ade80; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
        .status-conflict { background: #991b1b; color: #fca5a5; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .code { font-family: monospace; color: #4ade80; font-weight: bold; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 20px; }
        .alert-error { background: #7f1d1d; color: #fca5a5; padding: 12px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #ef4444; }
        .alert-success { background: #064e3b; color: #6ee7b7; padding: 12px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #10b981; }
    </style>
</head>
<body>
    <div class="container">
        {% if current_user.is_authenticated %}
        <div class="header-bar">
            <h1>نظام إدارة IPv6 المتقدم (Parent Pools & Subnets)</h1>
            <div>
                أهلاً بك، <strong>{{ current_user.username }}</strong> | <a href="/logout" style="color:#ef4444; text-decoration:none;">تسجيل الخروج</a>
            </div>
        </div>

        {% if error_msg %}
        <div class="alert-error">⚠️ {{ error_msg }}</div>
        {% endif %}

        {% if suggested %}
        <div class="alert-success">
            💡 <strong>العنوان الفارغ التالي المقتطع:</strong> <span class="code">{{ suggested }}</span> (تم تعبئته جاهزاً أدناه).
        </div>
        {% endif %}

        <!-- قسم الرينجات الأصلية -->
        <div class="card">
            <h3>1. الرينجات والكتل الأصلية (Parent Pools)</h3>
            <form method="POST" action="/add_pool" style="display: flex; gap: 10px; margin-bottom: 15px;">
                <input type="text" name="prefix" placeholder="الرينج الأصلي (مثال: 2a0a:4340::/29)" class="code" required style="flex: 2;">
                <input type="text" name="description" placeholder="الوصف (مثال: Luxe Main Block RIPE)" required style="flex: 3;">
                <button type="submit">إضافة رينج أصلي</button>
            </form>

            <table>
                <tr>
                    <th>الرينج الأصلي Parent Prefix</th>
                    <th>الوصف والملاحظات</th>
                    <th>طلب عنوان فارغ جديد</th>
                    <th>حذف Pool</th>
                </tr>
                {% for pool in pools %}
                <tr>
                    <td class="code">{{ pool.prefix }}</td>
                    <td>{{ pool.description }}</td>
                    <td>
                        <form method="POST" action="/extract_from_pool" style="display: flex; gap: 5px; align-items: center;">
                            <input type="hidden" name="pool_prefix" value="{{ pool.prefix }}">
                            <select name="target_len" style="padding: 4px;">
                                <option value="64">استخراج /64</option>
                                <option value="48">استخراج /48</option>
                                <option value="127">استخراج /127</option>
                            </select>
                            <button type="submit" class="action-btn">+ طلب عنوان فارغ</button>
                        </form>
                    </td>
                    <td><a href="/delete_pool/{{ pool.id }}"><button class="danger-btn" style="padding:4px 8px;">حذف</button></a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align:center;">لم تقم بإضافة رينجات أصلية بعد.</td></tr>
                {% endfor %}
            </table>
        </div>

        <!-- قسم التوثيق وإضافة الخدمة -->
        <div class="card">
            <h3>2. إدخال وتوثيق الخدمة (Service / Interface / Domain)</h3>
            <form method="POST" action="/add">
                <div class="form-grid">
                    <input type="text" name="code" placeholder="المعرف (L6730)" required>
                    <input type="text" name="interface_name" placeholder="Interface (Ethernet26/1)">
                    <input type="text" name="vlan_id" placeholder="VLAN (VLAN 51)">
                    <input type="text" name="subnet" placeholder="IPv6 Prefix" value="{{ suggested if suggested else '' }}" class="code" required>
                    <input type="text" name="domain" placeholder="الدومين الصوري (L6730.ipv6.luxeisp.com)" required>
                    <input type="text" name="next_hop" placeholder="Next Hop (2a0a:4340::1)">
                    <input type="text" name="description" placeholder="الوصف (PPPOE-SERVER)">
                </div>
                <button type="submit" style="margin-top: 15px; width: 100%;">حفظ الرينج في قاعدة البيانات</button>
            </form>
        </div>

        <!-- الجدول النهائي -->
        <div class="card">
            <h3>سجل الشبكة والخدمات المربوطة</h3>
            <table>
                <tr>
                    <th>المعرف</th>
                    <th>المنفذ</th>
                    <th>VLAN</th>
                    <th>IPv6 Prefix</th>
                    <th>الدومين الإداري</th>
                    <th>Next-Hop</th>
                    <th>الوصف والوجهة</th>
                    <th>فحص التداخل</th>
                    <th>إجراء</th>
                </tr>
                {% for item in items %}
                <tr>
                    <td><span class="tag">{{ item.rec.code }}</span></td>
                    <td class="code">{{ item.rec.interface_name or '-' }}</td>
                    <td>{{ item.rec.vlan_id or '-' }}</td>
                    <td class="code">{{ item.rec.subnet }}</td>
                    <td style="color:#38bdf8;">{{ item.rec.domain }}</td>
                    <td class="code">{{ item.rec.next_hop or '-' }}</td>
                    <td>{{ item.rec.description or '-' }}</td>
                    <td>
                        {% if item.has_conflict %}
                            <span class="status-conflict">⚠️ تضارب Overlap</span>
                        {% else %}
                            <span class="status-ok">سليم OK</span>
                        {% endif %}
                    </td>
                    <td><a href="/delete/{{ item.rec.id }}"><button class="danger-btn">حذف</button></a></td>
                </tr>
                {% else %}
                <tr><td colspan="9" style="text-align:center;">لا توجد خدمات موثقة بعد.</td></tr>
                {% endfor %}
            </table>
        </div>
        {% else %}
        <div style="max-width: 400px; margin: 80px auto;" class="card">
            <h2 style="text-align: center; color: #38bdf8;">تسجيل الدخول للنظام</h2>
            {% if login_error %}
            <p style="color: #ef4444; text-align: center;">{{ login_error }}</p>
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

def get_records_with_conflicts():
    records = NetworkRecord.query.all()
    items = []
    parsed_nets = []
    for r in records:
        try:
            parsed_nets.append((r, ipaddress.IPv6Network(r.subnet, strict=False)))
        except ValueError:
            parsed_nets.append((r, None))

    for r1, net1 in parsed_nets:
        has_conflict = False
        if net1:
            for r2, net2 in parsed_nets:
                if r1.id != r2.id and net2:
                    if net1.overlaps(net2):
                        has_conflict = True
                        break
        items.append({'rec': r1, 'has_conflict': has_conflict})
    return items

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template_string(HTML_LAYOUT)
    pools = ParentPool.query.all()
    items = get_records_with_conflicts()
    return render_template_string(HTML_LAYOUT, pools=pools, items=items)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect(url_for('index'))
    return render_template_string(HTML_LAYOUT, login_error="اسم المستخدم أو كلمة المرور غير صحيحة")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_pool', methods=['POST'])
@login_required
def add_pool():
    prefix_str = request.form.get('prefix')
    desc = request.form.get('description')
    try:
        ipaddress.IPv6Network(prefix_str, strict=False)
        new_pool = ParentPool(prefix=prefix_str, description=desc)
        db.session.add(new_pool)
        db.session.commit()
    except Exception as e:
        pools = ParentPool.query.all()
        items = get_records_with_conflicts()
        return render_template_string(HTML_LAYOUT, pools=pools, items=items, error_msg=f"خطأ في إضافة Pool: {str(e)}")
    return redirect(url_for('index'))

@app.route('/extract_from_pool', methods=['POST'])
@login_required
def extract_from_pool():
    pool_prefix = request.form.get('pool_prefix')
    target_len = int(request.form.get('target_len'))
    pools = ParentPool.query.all()
    items = get_records_with_conflicts()
    records = NetworkRecord.query.all()
    
    try:
        parent_net = ipaddress.IPv6Network(pool_prefix, strict=False)
        used_nets = [ipaddress.IPv6Network(r.subnet, strict=False) for r in records]
        
        suggested = None
        for sub in parent_net.subnets(new_prefix=target_len):
            if not any(sub.overlaps(u) for u in used_nets):
                suggested = str(sub)
                break
                
        if not suggested:
            return render_template_string(HTML_LAYOUT, pools=pools, items=items, error_msg="هذا الرينج ممتلئ بالكامل ولا توجد مساحة فارغة بهذا الحجم!")

        return render_template_string(HTML_LAYOUT, pools=pools, items=items, suggested=suggested)
    except Exception as e:
        return render_template_string(HTML_LAYOUT, pools=pools, items=items, error_msg=f"خطأ في الحساب: {str(e)}")

@app.route('/add', methods=['POST'])
@login_required
def add():
    subnet_str = request.form.get('subnet')
    pools = ParentPool.query.all()
    
    try:
        new_net = ipaddress.IPv6Network(subnet_str, strict=False)
        existing_records = NetworkRecord.query.all()
        
        for r in existing_records:
            try:
                ext_net = ipaddress.IPv6Network(r.subnet, strict=False)
                if new_net.overlaps(ext_net):
                    items = get_records_with_conflicts()
                    error_msg = f"الرينج {subnet_str} يتضارب مباشرة مع الرينج المضاف سابقاً ({r.subnet}) المربوط بـ {r.code}!"
                    return render_template_string(HTML_LAYOUT, pools=pools, items=items, error_msg=error_msg)
            except ValueError:
                continue
    except ValueError:
        items = get_records_with_conflicts()
        return render_template_string(HTML_LAYOUT, pools=pools, items=items, error_msg="صيغة الـ IPv6 Prefix غير صحيحة!")

    new_rec = NetworkRecord(
        code=request.form.get('code'),
        interface_name=request.form.get('interface_name'),
        vlan_id=request.form.get('vlan_id'),
        subnet=subnet_str,
        domain=request.form.get('domain'),
        next_hop=request.form.get('next_hop'),
        description=request.form.get('description')
    )
    db.session.add(new_rec)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_pool/<int:id>')
@login_required
def delete_pool(id):
    pool = ParentPool.query.get_or_404(id)
    db.session.delete(pool)
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
