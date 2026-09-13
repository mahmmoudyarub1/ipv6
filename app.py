from flask import Flask, request, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import ipaddress

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ipv6_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class IPv6Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    subnet = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(150), nullable=False)
    destination = db.Column(db.String(250), nullable=True)

with app.app_context():
    db.create_all()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>إدارة وتوثيق كتل IPv6</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 25px; }
        h1, h3 { color: #38bdf8; }
        .container { max-width: 1100px; margin: 0 auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; }
        .form-group { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
        input, button { padding: 10px 14px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
        input { flex: 1; min-width: 180px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; }
        button:hover { background: #0369a1; }
        .danger-btn { background: #ef4444; }
        .danger-btn:hover { background: #dc2626; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #334155; padding: 12px; text-align: right; }
        th { background: #334155; color: #38bdf8; }
        .tag { background: #0369a1; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .code-font { font-family: monospace; font-size: 14px; color: #4ade80; }
    </style>
</head>
<body>
    <div class="container">
        <h1>لوحة إدارة وتوثيق رينجات IPv6 (Database)</h1>
        
        <div class="card">
            <h3>1. البحث عن أول Subnet / IP فارغ تلقائياً</h3>
            <form method="POST" action="/suggest" class="form-group">
                <input type="text" name="parent" placeholder="الرينج الرئيسي (مثال: 2a0a:4340::/29)" required>
                <input type="number" name="prefixlen" placeholder="حجم القطع (مثال: 64)" value="64" required style="max-width: 120px;">
                <button type="submit">استخراج عنوان فارغ</button>
            </form>
            {% if suggested %}
            <p style="margin-top: 15px;">العنوان المقترح الفارغ القادم: <span class="code-font">{{ suggested }}</span></p>
            {% endif %}
        </div>

        <div class="card">
            <h3>2. إدخال وتوثيق رينج جديد</h3>
            <form method="POST" action="/add" class="form-group">
                <input type="text" name="code" placeholder="المعرف (مثال: L6730)" required style="max-width: 150px;">
                <input type="text" name="subnet" placeholder="IPv6 Prefix" value="{{ suggested if suggested else '' }}" required class="code-font">
                <input type="text" name="domain" placeholder="الدومين الصوري (L6730.ipv6.luxeisp.com)" required>
                <input type="text" name="destination" placeholder="تفاصيل والوجهة (مثال: Link to Erbil PoP)">
                <button type="submit">حفظ في السجل</button>
            </form>
        </div>

        <div class="card">
            <h3>سجل الرينجات المسجلة في قاعدة البيانات</h3>
            <table>
                <tr>
                    <th>المعرف</th>
                    <th>IPv6 Subnet</th>
                    <th>الدومين الصوري الإداري</th>
                    <th>الوجهة والتفاصيل</th>
                    <th>إجراء</th>
                </tr>
                {% for r in records %}
                <tr>
                    <td><span class="tag">{{ r.code }}</span></td>
                    <td class="code-font">{{ r.subnet }}</td>
                    <td style="color:#38bdf8;">{{ r.domain }}</td>
                    <td>{{ r.destination }}</td>
                    <td>
                        <a href="/delete/{{ r.id }}"><button class="danger-btn">حذف</button></a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="5" style="text-align:center;">لا توجد رينجات مسجلة حتى الآن.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    records = IPv6Record.query.all()
    return render_template_string(HTML_TEMPLATE, records=records)

@app.route('/suggest', methods=['POST'])
def suggest():
    parent_str = request.form.get('parent')
    prefixlen = int(request.form.get('prefixlen'))
    records = IPv6Record.query.all()
    
    try:
        parent_net = ipaddress.IPv6Network(parent_str, strict=False)
        used_nets = [ipaddress.IPv6Network(r.subnet, strict=False) for r in records]
        
        suggested = None
        for sub in parent_net.subnets(new_prefix=prefixlen):
            if not any(sub.overlaps(u) for u in used_nets):
                suggested = str(sub)
                break
                
        return render_template_string(HTML_TEMPLATE, records=records, suggested=suggested)
    except Exception as e:
        return f"خطأ في تنسيق IPv6: {str(e)}", 400

@app.route('/add', methods=['POST'])
def add():
    new_rec = IPv6Record(
        code=request.form.get('code'),
        subnet=request.form.get('subnet'),
        domain=request.form.get('domain'),
        destination=request.form.get('destination')
    )
    db.session.add(new_rec)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    rec = IPv6Record.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8787)
