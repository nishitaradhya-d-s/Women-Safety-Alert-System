from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3
import re
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "women-safety-app-secret-key-2024"
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 365  # 1 year

DB = "database.db"

# ----- Helper function for time ago -----
def get_time_ago(timestamp):
    if not timestamp:
        return 'Unknown'
    try:
        # Handle possible fractional seconds
        ts = datetime.strptime(timestamp.split('.')[0], '%Y-%m-%d %H:%M:%S')
    except:
        return 'Just now'
    now = datetime.now()
    diff = now - ts
    if diff.days > 0:
        return f'{diff.days}d ago'
    elif diff.seconds // 3600 > 0:
        return f'{diff.seconds // 3600}h ago'
    elif diff.seconds // 60 > 0:
        return f'{diff.seconds // 60}m ago'
    else:
        return 'Just now'

# ----- Database initialization -----
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        emergency1 TEXT NOT NULL,
        emergency2 TEXT NOT NULL,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_location TEXT,
        last_active TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS locations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lat REAL,
        lon REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sos_alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lat REAL,
        lon REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active',
        resolved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    c.execute("SELECT * FROM admin WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO admin (username, password) VALUES (?, ?)",
                  ('admin', 'admin123'))
    conn.commit()
    conn.close()

# ----- Decorators -----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_phone(phone):
    return re.match(r'^[6-9]\d{9}$', phone)

# ----- User Routes -----
@app.route("/")
def home():
    session.clear()
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    e1 = request.form.get("emergency1", "").strip()
    e2 = request.form.get("emergency2", "").strip()

    if not all([name, phone, e1, e2]):
        return render_template("register.html", error="All fields are required")
    if not validate_phone(phone):
        return render_template("register.html", error="Invalid phone number")
    if not validate_phone(e1):
        return render_template("register.html", error="Invalid emergency contact 1")
    if not validate_phone(e2):
        return render_template("register.html", error="Invalid emergency contact 2")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, phone, emergency1, emergency2) VALUES (?,?,?,?)",
                  (name, phone, e1, e2))
        conn.commit()
        user_id = c.lastrowid
        session.permanent = True
        session['user_id'] = user_id
        session['phone'] = phone
        session['name'] = name
        session['user_type'] = 'user'
        return redirect(url_for('dashboard'))
    except sqlite3.IntegrityError:
        c.execute("SELECT id, name FROM users WHERE phone = ?", (phone,))
        existing = c.fetchone()
        if existing:
            session.permanent = True
            session['user_id'] = existing[0]
            session['phone'] = phone
            session['name'] = existing[1]
            session['user_type'] = 'user'
            return redirect(url_for('dashboard'))
        else:
            return render_template("register.html", error="Registration failed")
    finally:
        conn.close()

@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, phone, emergency1, emergency2 FROM users WHERE id = ?", 
              (session['user_id'],))
    user = c.fetchone()
    c.execute("SELECT COUNT(*) FROM sos_alerts WHERE user_id = ? AND date(timestamp) = date('now')", 
              (session['user_id'],))
    today_alerts = c.fetchone()[0]
    conn.close()
    return render_template("dashboard.html", 
                         name=user[0], 
                         phone=user[1],
                         emergency1=user[2], 
                         emergency2=user[3],
                         today_alerts=today_alerts)

@app.route("/save-location", methods=["POST"])
@login_required
def save_location():
    try:
        data = request.json
        lat = data.get("lat")
        lon = data.get("lon")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO locations (user_id, lat, lon) VALUES (?,?,?)",
                  (session['user_id'], lat, lon))
        c.execute("UPDATE users SET last_location = ?, last_active = CURRENT_TIMESTAMP WHERE id = ?",
                  (f"{lat},{lon}", session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/trigger-sos", methods=["POST"])
@login_required
def trigger_sos():
    try:
        data = request.json
        lat = data.get("lat")
        lon = data.get("lon")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT name, phone, emergency1, emergency2 FROM users WHERE id = ?", 
                  (session['user_id'],))
        user = c.fetchone()
        c.execute("INSERT INTO sos_alerts (user_id, lat, lon) VALUES (?,?,?)",
                  (session['user_id'], lat, lon))
        conn.commit()
        conn.close()
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        timestamp = datetime.now().strftime("%I:%M %p")
        message = f"""🚨 SOS ALERT from {user[0]}!
📍 Location: {maps_link}
🕐 Time: {timestamp}
📞 Call back: {user[1]}"""
        return jsonify({
            "status": "success",
            "message": "SOS triggered",
            "emergency1": user[2],
            "emergency2": user[3],
            "alert_message": message,
            "maps_link": maps_link
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ----- Admin Routes -----
@app.route("/admin")
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template("admin_login.html")

@app.route("/admin/auth", methods=["POST"])
def admin_auth():
    username = request.form.get("username")
    password = request.form.get("password")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM admin WHERE username = ? AND password = ?", (username, password))
    admin = c.fetchone()
    conn.close()
    if admin:
        session['admin_id'] = admin[0]
        session['user_type'] = 'admin'
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template("admin_login.html", error="Invalid credentials")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Basic stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE date(registered_at) = date('now')")
    new_today = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sos_alerts WHERE status = 'active'")
    active_alerts = c.fetchone()[0]

    c.execute("""SELECT COUNT(*) FROM sos_alerts 
                 WHERE status = 'active' 
                 AND datetime(timestamp) > datetime('now', '-5 minutes')""")
    critical_alerts = c.fetchone()[0]

    c.execute("""SELECT COUNT(DISTINCT user_id) FROM locations 
                 WHERE datetime(timestamp) > datetime('now', '-10 minutes')""")
    online_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sos_alerts WHERE date(timestamp) = date('now')")
    today_alerts = c.fetchone()[0]

    c.execute("""SELECT COUNT(*) FROM sos_alerts 
                 WHERE date(timestamp) = date('now') AND status = 'resolved'""")
    resolved_today = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM locations WHERE date(timestamp) = date('now')")
    location_updates_today = c.fetchone()[0]

    c.execute("SELECT datetime(timestamp) FROM locations ORDER BY timestamp DESC LIMIT 1")
    last_update = c.fetchone()
    last_location_update = last_update[0] if last_update else 'No updates'

    # Active SOS alerts with details
    c.execute("""SELECT s.id, u.name, u.phone, u.emergency1, u.emergency2, 
                        s.lat, s.lon, s.timestamp,
                        CASE WHEN datetime(s.timestamp) > datetime('now', '-5 minutes') 
                             THEN 1 ELSE 0 END as is_critical
                 FROM sos_alerts s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.status = 'active'
                 ORDER BY s.timestamp DESC""")
    active_sos = c.fetchall()
    active_sos_alerts = []
    for alert in active_sos:
        time_ago = get_time_ago(alert[7])
        active_sos_alerts.append({
            'id': alert[0],
            'name': alert[1],
            'phone': alert[2],
            'emergency1': alert[3],
            'emergency2': alert[4],
            'lat': alert[5],
            'lon': alert[6],
            'time_ago': time_ago,
            'is_critical': alert[8]
        })

    # Online users list
    c.execute("""SELECT u.id, u.name, u.phone, u.last_location, 
                        datetime(u.last_active) as last_active
                 FROM users u
                 WHERE datetime(u.last_active) > datetime('now', '-10 minutes')
                 ORDER BY u.last_active DESC""")
    online = c.fetchall()
    online_users_list = []
    for user in online:
        online_users_list.append({
            'id': user[0],
            'name': user[1],
            'phone': user[2],
            'last_location': user[3],
            'last_active': get_time_ago(user[4]) if user[4] else 'Just now'
        })

    # Recent activities (combined timeline)
    c.execute("""SELECT 'sos' as type, u.name, s.timestamp, 
                        s.lat || ',' || s.lon as location,
                        'SOS Alert triggered' as description
                 FROM sos_alerts s
                 JOIN users u ON s.user_id = u.id
                 UNION ALL
                 SELECT 'location' as type, u.name, l.timestamp,
                        l.lat || ',' || l.lon as location,
                        'Location updated' as description
                 FROM locations l
                 JOIN users u ON l.user_id = u.id
                 UNION ALL
                 SELECT 'login' as type, u.name, u.registered_at,
                        NULL as location,
                        'User registered' as description
                 FROM users u
                 ORDER BY timestamp DESC
                 LIMIT 50""")
    activities = c.fetchall()
    recent_activities = []
    for act in activities:
        recent_activities.append({
            'type': act[0],
            'user_name': act[1],
            'time_ago': get_time_ago(act[2]),
            'location': act[3],
            'description': act[4]
        })

    # Recent locations
    c.execute("""SELECT u.name, l.lat, l.lon, l.timestamp
                 FROM locations l
                 JOIN users u ON l.user_id = u.id
                 ORDER BY l.timestamp DESC
                 LIMIT 20""")
    recent_locs = c.fetchall()
    recent_locations = []
    for loc in recent_locs:
        recent_locations.append({
            'user_name': loc[0],
            'lat': loc[1],
            'lon': loc[2],
            'time_ago': get_time_ago(loc[3])
        })

    # All users with additional info
    c.execute("""SELECT u.id, u.name, u.phone, u.emergency1, u.emergency2,
                        u.registered_at, u.last_active, u.last_location,
                        (SELECT COUNT(*) FROM sos_alerts WHERE user_id = u.id) as sos_count,
                        (SELECT COUNT(*) FROM sos_alerts WHERE user_id = u.id AND status = 'active') as active_sos,
                        CASE WHEN datetime(u.last_active) > datetime('now', '-10 minutes') 
                             THEN 1 ELSE 0 END as is_online
                 FROM users u
                 ORDER BY u.registered_at DESC""")
    all_users_data = c.fetchall()
    all_users = []
    for user in all_users_data:
        all_users.append({
            'id': user[0],
            'name': user[1],
            'phone': user[2],
            'emergency1': user[3],
            'emergency2': user[4],
            'registered_at': user[5],
            'last_active': get_time_ago(user[6]) if user[6] else None,
            'last_location': user[7],
            'sos_count': user[8],
            'has_active_sos': user[9] > 0,
            'is_online': user[10] == 1
        })

    conn.close()
    return render_template("admin_dashboard.html",
                         total_users=total_users,
                         new_today=new_today,
                         active_alerts=active_alerts,
                         critical_alerts=critical_alerts,
                         online_users=online_users,
                         today_alerts=today_alerts,
                         resolved_today=resolved_today,
                         location_updates_today=location_updates_today,
                         last_location_update=last_location_update,
                         active_sos_alerts=active_sos_alerts,
                         online_users_list=online_users_list,
                         recent_activities=recent_activities,
                         recent_locations=recent_locations,
                         all_users=all_users)

@app.route("/admin/users")
@admin_required
def admin_users():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT id, name, phone, emergency1, emergency2, 
                 registered_at, last_location, last_active 
                 FROM users ORDER BY registered_at DESC""")
    users = c.fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)

@app.route("/admin/user/<int:user_id>")
@admin_required
def admin_user_details(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT lat, lon, timestamp FROM locations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50", 
              (user_id,))
    locations = c.fetchall()
    c.execute("SELECT * FROM sos_alerts WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    sos_alerts = c.fetchall()
    conn.close()
    return render_template("admin_user_details.html", 
                         user=user, 
                         locations=locations, 
                         sos_alerts=sos_alerts)

@app.route("/admin/resolve-sos/<int:alert_id>", methods=["POST"])
@admin_required
def resolve_sos(alert_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE sos_alerts SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP WHERE id = ?", 
              (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)