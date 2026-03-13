import random
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import get_db

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)


# ---------- auth helpers ----------

def login_required(f):
    """Decorator that redirects to login if session is missing."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """Decorator that restricts access to specific roles."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------- context processor ----------

@app.context_processor
def inject_user():
    """Makes user info available to all templates."""
    return {
        'current_user': {
            'name': session.get('user_name', ''),
            'role': session.get('role', ''),
            'id': session.get('user_id'),
        }
    }


# ---------- auth routes ----------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')

        if not email or not password or not role:
            flash('All fields are required.', 'danger')
            return render_template('login.html')

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM users WHERE email = %s AND role = %s AND is_active = 1",
                    (email, role)
                )
                user = cur.fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid credentials or role mismatch.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'resident')
        flat_number = request.form.get('flat_number', '').strip()
        block = request.form.get('block', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('register.html')

        pw_hash = generate_password_hash(password)

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    flash('Email already registered.', 'danger')
                    return render_template('register.html')

                cur.execute(
                    """INSERT INTO users (name, email, password_hash, role, flat_number, block, phone)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (name, email, pw_hash, role, flat_number or None, block or None, phone or None)
                )
        finally:
            conn.close()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------- dashboard ----------

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {}
    notifications = []
    try:
        with conn.cursor() as cur:
            # today's visitors
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM visitors WHERE DATE(entry_time) = CURDATE()"
            )
            stats['visitors_today'] = cur.fetchone()['cnt']

            # pending complaints
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM complaints WHERE status IN ('Open', 'In Progress')"
            )
            stats['pending_complaints'] = cur.fetchone()['cnt']

            # parking available
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM parking_slots WHERE is_occupied = 0"
            )
            stats['available_parking'] = cur.fetchone()['cnt']

            # pending payments (current user or all for admin)
            if session['role'] == 'admin':
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM payments WHERE status IN ('Pending', 'Overdue')"
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM payments WHERE resident_id = %s AND status IN ('Pending', 'Overdue')",
                    (session['user_id'],)
                )
            stats['pending_payments'] = cur.fetchone()['cnt']

            # recent notifications
            role = session['role']
            cur.execute(
                """SELECT * FROM notifications
                   WHERE target_role IN ('all', %s)
                   ORDER BY created_at DESC LIMIT 5""",
                (role,)
            )
            notifications = cur.fetchall()
    finally:
        conn.close()

    return render_template('dashboard.html', stats=stats, notifications=notifications)


# ---------- visitor management ----------

@app.route('/visitors')
@login_required
def visitors():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM visitors ORDER BY entry_time DESC LIMIT 50"
            )
            visitor_list = cur.fetchall()
    finally:
        conn.close()
    return render_template('visitors.html', visitors=visitor_list)


@app.route('/visitors/add', methods=['POST'])
@login_required
@role_required('admin', 'guard')
def add_visitor():
    name = request.form.get('visitor_name', '').strip()
    phone = request.form.get('phone', '').strip()
    flat = request.form.get('visiting_flat', '').strip()
    block = request.form.get('visiting_block', '').strip()
    purpose = request.form.get('purpose', '').strip()

    if not name or not phone or not flat:
        flash('Visitor name, phone, and flat number are required.', 'danger')
        return redirect(url_for('visitors'))

    otp = str(random.randint(100000, 999999))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO visitors (visitor_name, phone, visiting_flat, visiting_block, purpose, otp, added_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (name, phone, flat, block or None, purpose or None, otp, session['user_id'])
            )
    finally:
        conn.close()

    flash(f'Visitor registered. OTP: {otp}', 'success')
    return redirect(url_for('visitors'))


@app.route('/visitors/verify/<int:visitor_id>', methods=['POST'])
@login_required
def verify_visitor(visitor_id):
    entered_otp = request.form.get('otp', '').strip()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT otp FROM visitors WHERE id = %s", (visitor_id,))
            row = cur.fetchone()
            if row and row['otp'] == entered_otp:
                cur.execute("UPDATE visitors SET otp_verified = 1 WHERE id = %s", (visitor_id,))
                flash('OTP verified.', 'success')
            else:
                flash('Invalid OTP.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('visitors'))


@app.route('/visitors/exit/<int:visitor_id>', methods=['POST'])
@login_required
@role_required('admin', 'guard')
def mark_visitor_exit(visitor_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE visitors SET exit_time = NOW() WHERE id = %s", (visitor_id,)
            )
    finally:
        conn.close()
    flash('Visitor exit recorded.', 'success')
    return redirect(url_for('visitors'))


# ---------- complaints ----------

@app.route('/complaints')
@login_required
def complaints():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if session['role'] == 'admin':
                cur.execute(
                    """SELECT c.*, u.name AS resident_name FROM complaints c
                       JOIN users u ON c.resident_id = u.id
                       ORDER BY c.created_at DESC LIMIT 50"""
                )
            else:
                cur.execute(
                    """SELECT c.*, u.name AS resident_name FROM complaints c
                       JOIN users u ON c.resident_id = u.id
                       WHERE c.resident_id = %s
                       ORDER BY c.created_at DESC LIMIT 50""",
                    (session['user_id'],)
                )
            complaint_list = cur.fetchall()
    finally:
        conn.close()
    return render_template('complaints.html', complaints=complaint_list)


@app.route('/complaints/add', methods=['POST'])
@login_required
@role_required('admin', 'resident')
def add_complaint():
    block = request.form.get('block', '').strip()
    flat = request.form.get('flat_number', '').strip()
    category = request.form.get('category', 'General').strip()
    description = request.form.get('description', '').strip()

    if not block or not flat or not description:
        flash('Block, flat number, and description are required.', 'danger')
        return redirect(url_for('complaints'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO complaints (resident_id, block, flat_number, category, description)
                   VALUES (%s, %s, %s, %s, %s)""",
                (session['user_id'], block, flat, category, description)
            )
    finally:
        conn.close()

    flash('Complaint lodged successfully.', 'success')
    return redirect(url_for('complaints'))


@app.route('/complaints/update/<int:complaint_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_complaint(complaint_id):
    status = request.form.get('status', '')
    remarks = request.form.get('admin_remarks', '').strip()

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE complaints SET status = %s, admin_remarks = %s WHERE id = %s",
                (status, remarks, complaint_id)
            )
    finally:
        conn.close()

    flash('Complaint updated.', 'success')
    return redirect(url_for('complaints'))


# ---------- parking ----------

@app.route('/parking')
@login_required
def parking():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ps.*, u.name AS owner_name, u.flat_number
                   FROM parking_slots ps
                   LEFT JOIN users u ON ps.assigned_to = u.id
                   ORDER BY ps.slot_label"""
            )
            slots = cur.fetchall()
    finally:
        conn.close()
    return render_template('parking.html', slots=slots)


@app.route('/parking/register', methods=['POST'])
@login_required
@role_required('admin')
def register_vehicle():
    slot_id = request.form.get('slot_id', '')
    resident_id = request.form.get('resident_id', '')
    vehicle_number = request.form.get('vehicle_number', '').strip()
    vehicle_type = request.form.get('vehicle_type', 'Car')

    if not slot_id or not resident_id or not vehicle_number:
        flash('All fields are required.', 'danger')
        return redirect(url_for('parking'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE parking_slots
                   SET is_occupied = 1, assigned_to = %s, vehicle_number = %s, vehicle_type = %s
                   WHERE id = %s AND is_occupied = 0""",
                (resident_id, vehicle_number, vehicle_type, slot_id)
            )
            if cur.rowcount == 0:
                flash('Slot is already occupied or does not exist.', 'danger')
            else:
                flash('Vehicle registered to parking slot.', 'success')
    finally:
        conn.close()

    return redirect(url_for('parking'))


@app.route('/parking/release/<int:slot_id>', methods=['POST'])
@login_required
@role_required('admin')
def release_slot(slot_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE parking_slots
                   SET is_occupied = 0, assigned_to = NULL, vehicle_number = NULL, vehicle_type = 'Car'
                   WHERE id = %s""",
                (slot_id,)
            )
    finally:
        conn.close()
    flash('Parking slot released.', 'success')
    return redirect(url_for('parking'))


# ---------- payments ----------

@app.route('/payments')
@login_required
def payments():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if session['role'] == 'admin':
                cur.execute(
                    """SELECT p.*, u.name AS resident_name, u.flat_number, u.block
                       FROM payments p
                       JOIN users u ON p.resident_id = u.id
                       ORDER BY p.due_date DESC LIMIT 50"""
                )
            else:
                cur.execute(
                    """SELECT p.*, u.name AS resident_name, u.flat_number, u.block
                       FROM payments p
                       JOIN users u ON p.resident_id = u.id
                       WHERE p.resident_id = %s
                       ORDER BY p.due_date DESC LIMIT 50""",
                    (session['user_id'],)
                )
            payment_list = cur.fetchall()

            # summary for current user
            total_due = 0
            if session['role'] != 'admin':
                cur.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE resident_id = %s AND status != 'Paid'",
                    (session['user_id'],)
                )
                total_due = cur.fetchone()['total']
            else:
                cur.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE status != 'Paid'"
                )
                total_due = cur.fetchone()['total']
    finally:
        conn.close()

    return render_template('payments.html', payments=payment_list, total_due=total_due)


@app.route('/payments/pay/<int:payment_id>', methods=['POST'])
@login_required
def pay_bill(payment_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            txn_ref = f"TXN-{random.randint(100000, 999999)}"
            cur.execute(
                """UPDATE payments SET status = 'Paid', paid_on = CURDATE(), transaction_ref = %s
                   WHERE id = %s AND status != 'Paid'""",
                (txn_ref, payment_id)
            )
            if cur.rowcount:
                flash(f'Payment recorded. Reference: {txn_ref}', 'success')
            else:
                flash('Payment already completed or not found.', 'warning')
    finally:
        conn.close()
    return redirect(url_for('payments'))


@app.route('/payments/generate', methods=['POST'])
@login_required
@role_required('admin')
def generate_bills():
    """Admin action to generate monthly bills for all active residents."""
    bill_period = request.form.get('bill_period', '').strip()
    amount = request.form.get('amount', '0')
    due_date = request.form.get('due_date', '')

    if not bill_period or not due_date:
        flash('Bill period and due date are required.', 'danger')
        return redirect(url_for('payments'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE role = 'resident' AND is_active = 1")
            residents = cur.fetchall()
            for r in residents:
                cur.execute(
                    """INSERT INTO payments (resident_id, bill_period, amount, due_date)
                       VALUES (%s, %s, %s, %s)""",
                    (r['id'], bill_period, amount, due_date)
                )
        flash(f'Bills generated for {len(residents)} residents.', 'success')
    finally:
        conn.close()
    return redirect(url_for('payments'))


# ---------- notifications (admin) ----------

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            role = session['role']
            cur.execute(
                """SELECT n.*, u.name AS author FROM notifications n
                   LEFT JOIN users u ON n.created_by = u.id
                   WHERE n.target_role IN ('all', %s)
                   ORDER BY n.created_at DESC LIMIT 30""",
                (role,)
            )
            notif_list = cur.fetchall()
    finally:
        conn.close()
    return render_template('notifications.html', notifications=notif_list)


@app.route('/notifications/add', methods=['POST'])
@login_required
@role_required('admin')
def add_notification():
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    target = request.form.get('target_role', 'all')

    if not title or not message:
        flash('Title and message are required.', 'danger')
        return redirect(url_for('notifications'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO notifications (title, message, target_role, created_by)
                   VALUES (%s, %s, %s, %s)""",
                (title, message, target, session['user_id'])
            )
    finally:
        conn.close()
    flash('Notification published.', 'success')
    return redirect(url_for('notifications'))


# ---------- admin: manage users ----------

@app.route('/admin/users')
@login_required
@role_required('admin')
def manage_users():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            user_list = cur.fetchall()
    finally:
        conn.close()
    return render_template('admin_users.html', users=user_list)


@app.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = NOT is_active WHERE id = %s AND id != %s",
                (user_id, session['user_id'])
            )
    finally:
        conn.close()
    flash('User status updated.', 'success')
    return redirect(url_for('manage_users'))


# ---------- run ----------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
