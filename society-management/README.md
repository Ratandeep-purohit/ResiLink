# ResiLink - Society Management System

A comprehensive society management solution built with Flask, featuring a flexible database backend that supports both SQLite (for development) and MySQL (for production).

## 🚀 Key Features

- **Authentication**: Role-based access for Admins, Guards, and Residents.
- **Visitor Management**: Track entries, exits, and verify visitors with OTPs.
- **Complaint System**: Lodge and track maintenance complaints.
- **Parking Management**: Manage slot allocation and vehicle registration.
- **Payment Tracking**: Generate and track monthly maintenance bills.
- **Internal Notifications**: Broadcast announcements to the entire society or specific roles.

## 🛠️ Technology Stack

- **Backend**: Python (Flask)
- **Database**: SQLite (Dev) / MySQL (Prod)
- **Frontend**: HTML5, Vanilla CSS, JavaScript
- **Security**: PBKDF2 password hashing via Werkzeug

## 📂 Project Structure

- `app.py`: Main application logic and routes.
- `db.py`: Multi-database connection wrapper (SQLite/MySQL compatibility layer).
- `config.py`: Configuration management.
- `migration.py`: Universal schema migration tool.
- `seed.py`: Database initialization and demo data seeder.
- `schema.sql`: Raw SQL definition for the database.
- `templates/`: Jinja2 HTML templates.
- `static/`: CSS and JavaScript assets.

## ⚙️ Setup & Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Duplicate `.env` or edit the existing one to set your database preferences:
   ```env
   USE_SQLITE=True  # Set to False to use MySQL
   ```

3. **Initialize Database**:
   Run the migration script to create tables and the seeder to add default accounts:
   ```bash
   python migration.py
   python seed.py
   ```

4. **Run the App**:
   ```bash
   python app.py
   ```
   Access the system at `http://127.0.0.1:5000`.

## 🔑 Default Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@society.com` | `admin123` |
| **Guard** | `guard@society.com` | `guard123` |
| **Resident** | `rahul@society.com` | `resident123` |

## 📅 Maintenance & Migration

### Switching to MySQL
For production deployment, update your `.env` with the MySQL credentials provided by the client and run:
```bash
python migration.py
```
The migration tool will automatically detect your MySQL configuration and set up the corresponding database and tables.
