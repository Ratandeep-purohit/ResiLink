"""
seed.py — Initialize database tables and insert default users.
Run once: python seed.py
"""
from db import get_db
from migration import migrate
from werkzeug.security import generate_password_hash
from config import Config

def seed_users():
    """Insert default users if they don't exist."""
    conn = get_db()
    
    defaults = [
        {
            'name': 'Admin User',
            'email': 'admin@society.com',
            'password': 'admin123',
            'role': 'admin',
            'flat_number': None,
            'block': None,
            'phone': '9999999999',
        },
        {
            'name': 'Gate Guard',
            'email': 'guard@society.com',
            'password': 'guard123',
            'role': 'guard',
            'flat_number': None,
            'block': None,
            'phone': '8888888888',
        },
        {
            'name': 'Rahul Sharma',
            'email': 'rahul@society.com',
            'password': 'resident123',
            'role': 'resident',
            'flat_number': '101',
            'block': 'A',
            'phone': '7777777777',
        },
        {
            'name': 'Priya Patel',
            'email': 'priya@society.com',
            'password': 'resident123',
            'role': 'resident',
            'flat_number': '205',
            'block': 'B',
            'phone': '6666666666',
        },
    ]

    try:
        with conn.cursor() as cur:
            for u in defaults:
                cur.execute("SELECT id FROM users WHERE email = %s", (u['email'],))
                if cur.fetchone():
                    print(f"  User '{u['email']}' already exists, skipping.")
                    continue

                pw_hash = generate_password_hash(u['password'])
                cur.execute(
                    """INSERT INTO users (name, email, password_hash, role, flat_number, block, phone)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (u['name'], u['email'], pw_hash, u['role'],
                     u['flat_number'], u['block'], u['phone'])
                )
                print(f"  Created user: {u['email']} / {u['password']} ({u['role']})")
        print("[OK] Users seeded.")
    finally:
        conn.close()


def seed_sample_data():
    """Insert some sample data for demo purposes."""
    conn = get_db()

    try:
        with conn.cursor() as cur:
            # Check if we already have sample data
            cur.execute("SELECT COUNT(*) AS cnt FROM notifications")
            row = cur.fetchone()
            if row and row['cnt'] > 0:
                print("  Sample data already present, skipping.")
                return

            # Get user IDs
            cur.execute("SELECT id, role FROM users")
            users_list = cur.fetchall()
            users = {row['role']: row['id'] for row in users_list}
            admin_id = users.get('admin')
            
            cur.execute("SELECT id FROM users WHERE role = 'resident' ORDER BY id")
            residents = cur.fetchall()
            resident_id_1 = residents[0]['id'] if len(residents) >= 1 else None
            resident_id_2 = residents[1]['id'] if len(residents) >= 2 else None

            guard_id = users.get('guard')

            # Sample notifications
            notifications = [
                ('Monthly Meeting', 'Society monthly meeting scheduled for Sunday 10 AM at the clubhouse.', 'all', admin_id),
                ('Maintenance Notice', 'Water tank cleaning scheduled for Saturday. Water supply will be off from 10 AM to 2 PM.', 'all', admin_id),
                ('Security Update', 'New entry guidelines for delivery personnel effective next week. Please share OTP with visitors.', 'guard', admin_id),
            ]
            for title, msg, target, by in notifications:
                cur.execute(
                    "INSERT INTO notifications (title, message, target_role, created_by) VALUES (%s, %s, %s, %s)",
                    (title, msg, target, by)
                )

            # Sample complaints
            if resident_id_1:
                cur.execute(
                    """INSERT INTO complaints (resident_id, block, flat_number, category, description, status)
                       VALUES (%s, 'A', '101', 'Plumbing', 'Leaking pipe in kitchen. Water dripping continuously.', 'In Progress')""",
                    (resident_id_1,)
                )
            if resident_id_2:
                cur.execute(
                    """INSERT INTO complaints (resident_id, block, flat_number, category, description, status)
                       VALUES (%s, 'B', '205', 'Electrical', 'Corridor light on 2nd floor not working for 3 days.', 'Open')""",
                    (resident_id_2,)
                )

            # Sample visitors
            if guard_id:
                cur.execute(
                    """INSERT INTO visitors (visitor_name, phone, visiting_flat, visiting_block, purpose, otp, otp_verified, added_by)
                       VALUES ('Rajesh Kumar', '9876543210', '101', 'A', 'Guest', '123456', 1, %s)""",
                    (guard_id,)
                )
                cur.execute(
                    """INSERT INTO visitors (visitor_name, phone, visiting_flat, visiting_block, purpose, otp, otp_verified, added_by, exit_time)
                       VALUES ('Amazon Delivery', '9123456780', '205', 'B', 'Delivery', '654321', 1, %s, NOW())""",
                    (guard_id,)
                )

            # Sample payments
            if resident_id_1:
                cur.execute(
                    """INSERT INTO payments (resident_id, bill_period, amount, due_date, status)
                       VALUES (%s, 'March 2026', 2500.00, '2026-03-31', 'Pending')""",
                    (resident_id_1,)
                )
                cur.execute(
                    """INSERT INTO payments (resident_id, bill_period, amount, due_date, paid_on, status, transaction_ref)
                       VALUES (%s, 'February 2026', 2500.00, '2026-02-28', '2026-02-25', 'Paid', 'TXN-482910')""",
                    (resident_id_1,)
                )
            if resident_id_2:
                cur.execute(
                    """INSERT INTO payments (resident_id, bill_period, amount, due_date, status)
                       VALUES (%s, 'March 2026', 2500.00, '2026-03-31', 'Pending')""",
                    (resident_id_2,)
                )

            # Assign a couple of parking slots
            if resident_id_1:
                cur.execute(
                    """UPDATE parking_slots SET is_occupied = 1, assigned_to = %s,
                       vehicle_number = 'MH 02 XZ 9999', vehicle_type = 'Car'
                       WHERE slot_label = 'P-02'""",
                    (resident_id_1,)
                )
            if resident_id_2:
                cur.execute(
                    """UPDATE parking_slots SET is_occupied = 1, assigned_to = %s,
                       vehicle_number = 'MH 12 YR 5555', vehicle_type = 'Bike'
                       WHERE slot_label = 'P-05'""",
                    (resident_id_2,)
                )

            print("[OK] Sample data seeded.")
    finally:
        conn.close()


if __name__ == '__main__':
    print("Setting up Society Management database...\n")
    migrate()
    seed_users()
    seed_sample_data()
    print("\nDone! You can now run: python app.py")
    print("\nDefault logins:")
    print("  Admin    — admin@society.com    / admin123")
    print("  Guard    — guard@society.com    / guard123")
    print("  Resident — rahul@society.com    / resident123")
    print("  Resident — priya@society.com    / resident123")
    print("\nDone! You can now run: python app.py")
    print("\nDefault logins:")
    print("  Admin    — admin@society.com    / admin123")
    print("  Guard    — guard@society.com    / guard123")
    print("  Resident — rahul@society.com    / resident123")
    print("  Resident — priya@society.com    / resident123")
