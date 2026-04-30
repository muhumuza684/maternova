from measurement_theory import (
    classify_blood_pressure,
    classify_heart_rate,
    classify_temperature,
    classify_oxygen_saturation,
    compute_patient_risk_score,
    validate_vital_sign,
    BPCategory
)

from flask import Flask, render_template_string, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32)

_db_url = os.environ.get('DATABASE_URL', 'sqlite:///maternova.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ==================== MODELS ====================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='nurse')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    blood_type = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VitalSign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    respiratory_rate = db.Column(db.Integer)
    oxygen_saturation = db.Column(db.Integer)
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.String(100))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='vitals')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(20), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='appointments')

class PregnancyRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    gravida = db.Column(db.Integer)
    para = db.Column(db.Integer)
    last_menstrual_period = db.Column(db.String(20))
    estimated_delivery_date = db.Column(db.String(20))
    gestational_weeks = db.Column(db.Integer)
    risk_level = db.Column(db.String(20))
    notes = db.Column(db.Text)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='pregnancies')

class MedicalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    condition_name = db.Column(db.String(200), nullable=False)
    diagnosis_date = db.Column(db.String(20))
    status = db.Column(db.String(50))
    treatment = db.Column(db.Text)
    medications = db.Column(db.Text)
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.String(100))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='medical_histories')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@maternova.com',
            password=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            hospital='Main Hospital',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("\n" + "="*50)
        print("✓ SYSTEM READY!")
        print("  Admin Login: admin / admin123")
        print("="*50 + "\n")

# ==================== TEMPLATES ====================
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center min-vh-100 align-items-center">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-primary text-white text-center">
                        <h3>Maternova Login</h3>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="mb-3">
                                <label>Username</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login</button>
                        </form>
                    </div>
                    <div class="card-footer text-center">
                        <a href="/register">Create New Account</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center min-vh-100 align-items-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white text-center">
                        <h3>Create Account</h3>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>First Name</label>
                                    <input type="text" name="first_name" class="form-control" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Last Name</label>
                                    <input type="text" name="last_name" class="form-control" required>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Username</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="email" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Hospital Name</label>
                                <input type="text" name="hospital" class="form-control" placeholder="e.g., City Hospital" required>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Password</label>
                                    <input type="password" name="password" class="form-control" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Confirm Password</label>
                                    <input type="password" name="confirm_password" class="form-control" required>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Register</button>
                        </form>
                    </div>
                    <div class="card-footer text-center">
                        <a href="/login">Already have an account? Login</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Maternova</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .navbar-brand { font-weight: bold; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .card:hover { transform: translateY(-5px); }
        .stat-card { cursor: pointer; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text text-white me-3">
                    <i class="fas fa-user-circle"></i> {{ current_user.first_name }} {{ current_user.last_name }} ({{ current_user.role }})
                </span>
                <a class="nav-link" href="/patients">
                    <i class="fas fa-users"></i> Patients
                </a>
                <a class="nav-link" href="/analytics">
                    <i class="fas fa-chart-bar"></i> Analytics
                </a>
                <a class="nav-link" href="/logout">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <h2><i class="fas fa-tachometer-alt"></i> Dashboard</h2>
                <p class="text-muted">Welcome to {{ current_user.hospital }}</p>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="card bg-primary text-white stat-card" onclick="window.location='/patients'">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h6>Total Patients</h6>
                                <h2 class="display-4">{{ patients_count }}</h2>
                            </div>
                            <i class="fas fa-users fa-3x opacity-50"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card bg-success text-white stat-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h6>Vital Signs</h6>
                                <h2 class="display-4">{{ vitals_count }}</h2>
                            </div>
                            <i class="fas fa-heartbeat fa-3x opacity-50"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card bg-info text-white stat-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h6>Appointments</h6>
                                <h2 class="display-4">{{ appointments_count }}</h2>
                            </div>
                            <i class="fas fa-calendar-alt fa-3x opacity-50"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card bg-warning text-white stat-card" onclick="window.location='/analytics'">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h6>Pregnancies</h6>
                                <h2 class="display-4">{{ pregnancies_count }}</h2>
                            </div>
                            <i class="fas fa-baby fa-3x opacity-50"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0"><i class="fas fa-clock"></i> Recent Patients</h5>
                <a href="/analytics" class="btn btn-sm btn-outline-dark">
                    <i class="fas fa-chart-bar"></i> Risk Analytics
                </a>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>DOB</th>
                                <th>Gender</th>
                                <th>Phone</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for patient in recent_patients %}
                            <tr>
                                <td>{{ patient.first_name }} {{ patient.last_name }}</td>
                                <td>{{ patient.date_of_birth }}</td>
                                <td>{{ patient.gender }}</td>
                                <td>{{ patient.phone or 'N/A' }}</td>
                                <td>
                                    <a href="/patients/{{ patient.id }}" class="btn btn-sm btn-info">View</a>
                                    <a href="/vitals/{{ patient.id }}" class="btn btn-sm btn-success">Vitals</a>
                                    <a href="/appointments/{{ patient.id }}" class="btn btn-sm btn-primary">Appt</a>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="5" class="text-center">No patients yet. <a href="/patients/create">Add your first patient</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <div class="text-center mt-3">
                    <a href="/patients" class="btn btn-primary">View All Patients</a>
                    <a href="/patients/create" class="btn btn-success">Add New Patient</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

PATIENTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Patients - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Fraunces:wght@600&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        body {
            background: #f5f3ef;
            font-family: 'DM Sans', sans-serif;
            color: #1a1916;
        }

        /* ---- NAVBAR ---- */
        .navbar {
            background: #1a1916 !important;
            padding: 0.75rem 0;
            border-bottom: none;
        }
        .navbar-brand {
            font-family: 'Fraunces', serif;
            font-size: 1.25rem;
            color: #f5f3ef !important;
            letter-spacing: -0.02em;
        }
        .navbar-brand span { color: #d4a96a; }
        .nav-link {
            color: #a09e99 !important;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            transition: color 0.2s;
        }
        .nav-link:hover { color: #f5f3ef !important; }
        .nav-link.active { color: #d4a96a !important; }

        /* ---- PAGE HEADER ---- */
        .page-header {
            padding: 2rem 0 1.5rem;
        }
        .page-header h1 {
            font-family: 'Fraunces', serif;
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            margin: 0 0 0.25rem;
        }
        .page-header p {
            color: #6b6963;
            font-size: 0.9rem;
            margin: 0;
        }

        /* ---- SEARCH BAR ---- */
        .search-bar-wrap {
            background: #fff;
            border: 1.5px solid #e0ddd7;
            border-radius: 12px;
            display: flex;
            align-items: center;
            padding: 0 1rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .search-bar-wrap:focus-within {
            border-color: #d4a96a;
            box-shadow: 0 0 0 3px rgba(212,169,106,0.15);
        }
        .search-bar-wrap i {
            color: #a09e99;
            font-size: 0.9rem;
            margin-right: 10px;
        }
        .search-bar-wrap input {
            border: none;
            outline: none;
            width: 100%;
            padding: 0.75rem 0;
            font-family: 'DM Sans', sans-serif;
            font-size: 0.92rem;
            background: transparent;
            color: #1a1916;
        }
        .search-bar-wrap input::placeholder { color: #b0ada7; }

        /* ---- FILTER PILLS ---- */
        .filter-row {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .filter-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #a09e99;
            margin-right: 4px;
        }
        .filter-pill {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 14px;
            border-radius: 99px;
            border: 1.5px solid #e0ddd7;
            background: #fff;
            font-size: 0.82rem;
            font-weight: 500;
            color: #4a4843;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }
        .filter-pill:hover {
            border-color: #d4a96a;
            color: #b07d2e;
        }
        .filter-pill.active {
            background: #1a1916;
            border-color: #1a1916;
            color: #f5f3ef;
        }
        .filter-pill .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        /* ---- SORT SELECT ---- */
        .sort-select {
            border: 1.5px solid #e0ddd7;
            border-radius: 8px;
            padding: 6px 32px 6px 12px;
            font-family: 'DM Sans', sans-serif;
            font-size: 0.82rem;
            font-weight: 500;
            color: #4a4843;
            background: #fff;
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23a09e99'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
            outline: none;
            transition: border-color 0.2s;
        }
        .sort-select:focus { border-color: #d4a96a; }

        /* ---- STATS BAR ---- */
        .stats-bar {
            display: flex;
            gap: 24px;
            padding: 1rem 1.25rem;
            background: #fff;
            border: 1.5px solid #e0ddd7;
            border-radius: 12px;
            flex-wrap: wrap;
        }
        .stat-item { text-align: center; }
        .stat-item .val {
            font-family: 'Fraunces', serif;
            font-size: 1.4rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            line-height: 1;
        }
        .stat-item .lbl {
            font-size: 0.72rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #a09e99;
            margin-top: 2px;
        }
        .stat-sep { width: 1px; background: #e0ddd7; align-self: stretch; }

        /* ---- PATIENT TABLE ---- */
        .patient-table-wrap {
            background: #fff;
            border: 1.5px solid #e0ddd7;
            border-radius: 14px;
            overflow: hidden;
        }
        .patient-table {
            width: 100%;
            border-collapse: collapse;
        }
        .patient-table thead tr {
            border-bottom: 1.5px solid #e0ddd7;
        }
        .patient-table thead th {
            padding: 0.85rem 1.25rem;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: #a09e99;
            background: #faf9f6;
            white-space: nowrap;
            cursor: pointer;
            user-select: none;
        }
        .patient-table thead th:hover { color: #4a4843; }
        .patient-table thead th .sort-icon { opacity: 0.4; margin-left: 4px; font-size: 0.65rem; }
        .patient-table thead th.sorted .sort-icon { opacity: 1; color: #d4a96a; }

        .patient-table tbody tr {
            border-bottom: 1px solid #f0ede8;
            transition: background 0.12s;
            cursor: pointer;
        }
        .patient-table tbody tr:last-child { border-bottom: none; }
        .patient-table tbody tr:hover { background: #faf8f4; }
        .patient-table tbody tr.hidden { display: none; }

        .patient-table td {
            padding: 1rem 1.25rem;
            font-size: 0.88rem;
            vertical-align: middle;
        }

        /* avatar + name cell */
        .patient-name-cell { display: flex; align-items: center; gap: 12px; }
        .avatar {
            width: 38px; height: 38px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.78rem; font-weight: 600;
            flex-shrink: 0;
        }
        .avatar-F { background: #fbeaf0; color: #993556; }
        .avatar-M { background: #e6f1fb; color: #185fa5; }
        .patient-full-name { font-weight: 600; font-size: 0.9rem; }
        .patient-dob { font-size: 0.78rem; color: #a09e99; margin-top: 1px; }

        /* badges */
        .badge-blood {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.76rem;
            font-weight: 600;
            background: #fcebeb;
            color: #a32d2d;
        }
        .badge-gender {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 99px;
            font-size: 0.76rem;
            font-weight: 500;
        }
        .badge-gender.F { background: #fbeaf0; color: #993556; }
        .badge-gender.M { background: #e6f1fb; color: #185fa5; }

        /* action buttons */
        .action-group { display: flex; gap: 6px; }
        .btn-action {
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 500;
            border: 1.5px solid transparent;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
            white-space: nowrap;
        }
        .btn-action.profile  { background: #f5f3ef; border-color: #e0ddd7; color: #4a4843; }
        .btn-action.profile:hover  { background: #ede9e1; }
        .btn-action.vitals   { background: #eaf3de; border-color: #c0dd97; color: #3b6d11; }
        .btn-action.vitals:hover   { background: #d5e9b8; }
        .btn-action.appt     { background: #e6f1fb; border-color: #b5d4f4; color: #185fa5; }
        .btn-action.appt:hover     { background: #cce3f6; }
        .btn-action.preg     { background: #faeeda; border-color: #fac775; color: #854f0b; }
        .btn-action.preg:hover     { background: #f5dba8; }

        /* ---- EMPTY STATE ---- */
        .empty-state {
            padding: 4rem 1rem;
            text-align: center;
        }
        .empty-state i { font-size: 2.5rem; color: #d3d1c7; margin-bottom: 1rem; }
        .empty-state h5 { font-family: 'Fraunces', serif; color: #4a4843; margin-bottom: 0.5rem; }
        .empty-state p { color: #a09e99; font-size: 0.88rem; }

        /* ---- ADD PATIENT BTN ---- */
        .btn-add-patient {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: #1a1916;
            color: #f5f3ef;
            border: none;
            border-radius: 10px;
            font-family: 'DM Sans', sans-serif;
            font-size: 0.88rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.15s;
        }
        .btn-add-patient:hover { background: #2e2c28; color: #f5f3ef; text-decoration: none; }
        .btn-add-patient i { font-size: 0.8rem; }

        /* ---- RESULT COUNT ---- */
        .result-count {
            font-size: 0.82rem;
            color: #a09e99;
        }
        .result-count span { color: #1a1916; font-weight: 600; }

        /* ---- NO RESULTS MSG ---- */
        #no-results-row { display: none; }
        #no-results-row td { padding: 3rem; text-align: center; color: #a09e99; font-size: 0.9rem; }
    </style>
</head>
<body>

    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">Matern<span>o</span>va</a>
            <div class="navbar-nav ms-auto d-flex flex-row gap-3">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link active" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container">

        <!-- Page header -->
        <div class="page-header d-flex justify-content-between align-items-start">
            <div>
                <h1>Patients</h1>
                <p>{{ current_user.hospital }}</p>
            </div>
            <a href="/patients/create" class="btn-add-patient mt-2">
                <i class="fas fa-plus"></i> Add Patient
            </a>
        </div>

        <!-- Stats bar -->
        <div class="stats-bar mb-3" id="stats-bar">
            <div class="stat-item">
                <div class="val" id="stat-total">{{ patients|length }}</div>
                <div class="lbl">Total</div>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item">
                <div class="val" id="stat-female" style="color:#993556;">—</div>
                <div class="lbl">Female</div>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item">
                <div class="val" id="stat-male" style="color:#185fa5;">—</div>
                <div class="lbl">Male</div>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item">
                <div class="val" id="stat-visible">{{ patients|length }}</div>
                <div class="lbl">Showing</div>
            </div>
        </div>

        <!-- Search + Filters row -->
        <div class="d-flex gap-3 mb-3 flex-wrap align-items-center">
            <div class="search-bar-wrap flex-grow-1" style="min-width:220px; max-width:440px;">
                <i class="fas fa-search"></i>
                <input type="text" id="searchInput" placeholder="Search by name, phone, blood type…" autocomplete="off">
            </div>

            <div class="filter-row">
                <span class="filter-label">Gender</span>
                <button class="filter-pill active" data-filter="gender" data-value="all">
                    All
                </button>
                <button class="filter-pill" data-filter="gender" data-value="Female">
                    <span class="dot" style="background:#d4537e;"></span> Female
                </button>
                <button class="filter-pill" data-filter="gender" data-value="Male">
                    <span class="dot" style="background:#378add;"></span> Male
                </button>
            </div>

            <div class="filter-row">
                <span class="filter-label">Blood</span>
                <select id="bloodFilter" class="sort-select">
                    <option value="all">Any type</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                </select>
            </div>

            <div class="filter-row">
                <span class="filter-label">Sort</span>
                <select id="sortSelect" class="sort-select">
                    <option value="name-asc">Name A–Z</option>
                    <option value="name-desc">Name Z–A</option>
                    <option value="dob-asc">Oldest first</option>
                    <option value="dob-desc">Youngest first</option>
                    <option value="recent">Recently added</option>
                </select>
            </div>
        </div>

        <!-- Result count -->
        <div class="mb-2 result-count">
            Showing <span id="visible-count">{{ patients|length }}</span> of <span>{{ patients|length }}</span> patients
        </div>

        <!-- Table -->
        <div class="patient-table-wrap mb-5">
            <table class="patient-table" id="patientTable">
                <thead>
                    <tr>
                        <th>Patient</th>
                        <th>Gender</th>
                        <th>Blood Type</th>
                        <th>Phone</th>
                        <th>Date of Birth</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="patientBody">
                    {% for patient in patients %}
                    <tr
                        data-name="{{ patient.first_name|lower }} {{ patient.last_name|lower }}"
                        data-gender="{{ patient.gender }}"
                        data-blood="{{ patient.blood_type or '' }}"
                        data-phone="{{ patient.phone or '' }}"
                        data-dob="{{ patient.date_of_birth }}"
                        data-id="{{ patient.id }}"
                    >
                        <td>
                            <div class="patient-name-cell">
                                <div class="avatar avatar-{{ 'F' if patient.gender == 'Female' else 'M' }}">
                                    {{ patient.first_name[0] }}{{ patient.last_name[0] }}
                                </div>
                                <div>
                                    <div class="patient-full-name">{{ patient.first_name }} {{ patient.last_name }}</div>
                                    <div class="patient-dob">{{ patient.email or 'No email' }}</div>
                                </div>
                            </div>
                        </td>
                        <td>
                            <span class="badge-gender {{ 'F' if patient.gender == 'Female' else 'M' }}">
                                {{ patient.gender }}
                            </span>
                        </td>
                        <td>
                            {% if patient.blood_type %}
                            <span class="badge-blood">{{ patient.blood_type }}</span>
                            {% else %}
                            <span style="color:#b0ada7; font-size:0.82rem;">—</span>
                            {% endif %}
                        </td>
                        <td style="color:#6b6963; font-size:0.85rem;">{{ patient.phone or '—' }}</td>
                        <td style="color:#6b6963; font-size:0.85rem;">{{ patient.date_of_birth }}</td>
                        <td>
                            <div class="action-group">
                                <a href="/patients/{{ patient.id }}" class="btn-action profile">Profile</a>
                                <a href="/vitals/{{ patient.id }}" class="btn-action vitals">Vitals</a>
                                <a href="/appointments/{{ patient.id }}" class="btn-action appt">Appt</a>
                                <a href="/pregnancy/{{ patient.id }}" class="btn-action preg">Pregnancy</a>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                    <tr id="no-results-row">
                        <td colspan="6">
                            <i class="fas fa-search" style="display:block; text-align:center; font-size:1.5rem; color:#d3d1c7; margin-bottom:0.5rem;"></i>
                            No patients match your search. <a href="/patients/create" style="color:#d4a96a;">Add a new patient?</a>
                        </td>
                    </tr>
                </tbody>
            </table>

            {% if not patients %}
            <div class="empty-state">
                <i class="fas fa-users"></i>
                <h5>No patients yet</h5>
                <p>Add your first patient to get started.</p>
                <a href="/patients/create" class="btn-add-patient" style="margin: 0 auto;">
                    <i class="fas fa-plus"></i> Add Patient
                </a>
            </div>
            {% endif %}
        </div>

    </div>

    <script>
    (function() {
        const searchInput = document.getElementById('searchInput');
        const bloodFilter = document.getElementById('bloodFilter');
        const sortSelect  = document.getElementById('sortSelect');
        const tbody       = document.getElementById('patientBody');
        const noResults   = document.getElementById('no-results-row');
        const visibleCount = document.getElementById('visible-count');
        const statFemale  = document.getElementById('stat-female');
        const statMale    = document.getElementById('stat-male');
        const statVisible = document.getElementById('stat-visible');

        let activeGender = 'all';

        // Compute totals once
        const allRows = Array.from(tbody.querySelectorAll('tr[data-id]'));
        let femaleTotal = 0, maleTotal = 0;
        allRows.forEach(r => {
            if (r.dataset.gender === 'Female') femaleTotal++;
            else maleTotal++;
        });
        statFemale.textContent = femaleTotal;
        statMale.textContent   = maleTotal;

        // Gender pills
        document.querySelectorAll('[data-filter="gender"]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('[data-filter="gender"]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeGender = btn.dataset.value;
                applyFilters();
            });
        });

        searchInput.addEventListener('input', applyFilters);
        bloodFilter.addEventListener('change', applyFilters);
        sortSelect.addEventListener('change', () => { applyFilters(); });

        function applyFilters() {
            const query = searchInput.value.trim().toLowerCase();
            const blood = bloodFilter.value;

            // Filter
            let visible = [];
            allRows.forEach(row => {
                const nameMatch  = !query || row.dataset.name.includes(query)
                                          || row.dataset.phone.includes(query)
                                          || row.dataset.blood.toLowerCase().includes(query);
                const genderMatch = activeGender === 'all' || row.dataset.gender === activeGender;
                const bloodMatch  = blood === 'all' || row.dataset.blood === blood;

                const show = nameMatch && genderMatch && bloodMatch;
                row.classList.toggle('hidden', !show);
                if (show) visible.push(row);
            });

            // Sort
            const sort = sortSelect.value;
            visible.sort((a, b) => {
                if (sort === 'name-asc')  return a.dataset.name.localeCompare(b.dataset.name);
                if (sort === 'name-desc') return b.dataset.name.localeCompare(a.dataset.name);
                if (sort === 'dob-asc')  return a.dataset.dob.localeCompare(b.dataset.dob);
                if (sort === 'dob-desc') return b.dataset.dob.localeCompare(a.dataset.dob);
                return 0; // 'recent' = original DOM order
            });

            // Re-append in sorted order
            visible.forEach(row => tbody.appendChild(row));

            // No-results row
            noResults.style.display = visible.length === 0 ? 'table-row' : 'none';

            // Update count
            visibleCount.textContent = visible.length;
            statVisible.textContent  = visible.length;
        }

        // Row click navigates to profile (except clicking action buttons)
        allRows.forEach(row => {
            row.addEventListener('click', (e) => {
                if (e.target.closest('.action-group')) return;
                window.location = '/patients/' + row.dataset.id;
            });
        });
    })();
    </script>

</body>
</html>
'''

PATIENT_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Add Patient - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5><i class="fas fa-user-plus"></i> Add New Patient</h5>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>First Name *</label>
                                    <input type="text" name="first_name" class="form-control" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Last Name *</label>
                                    <input type="text" name="last_name" class="form-control" required>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Date of Birth *</label>
                                    <input type="date" name="date_of_birth" class="form-control" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Gender *</label>
                                    <select name="gender" class="form-control" required>
                                        <option value="">Select</option>
                                        <option value="Female">Female</option>
                                        <option value="Male">Male</option>
                                    </select>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Phone</label>
                                    <input type="text" name="phone" class="form-control">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Email</label>
                                    <input type="email" name="email" class="form-control">
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Address</label>
                                <textarea name="address" class="form-control" rows="2"></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Blood Type</label>
                                    <select name="blood_type" class="form-control">
                                        <option value="">Select</option>
                                        <option value="A+">A+</option>
                                        <option value="A-">A-</option>
                                        <option value="B+">B+</option>
                                        <option value="B-">B-</option>
                                        <option value="O+">O+</option>
                                        <option value="O-">O-</option>
                                        <option value="AB+">AB+</option>
                                        <option value="AB-">AB-</option>
                                    </select>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Allergies</label>
                                    <input type="text" name="allergies" class="form-control" placeholder="e.g., Penicillin, Latex">
                                </div>
                            </div>
                            <div class="text-end">
                                <a href="/patients" class="btn btn-secondary">Cancel</a>
                                <button type="submit" class="btn btn-primary">Create Patient</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

VITALS_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Vital Signs - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .vital-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card vital-card">
                    <div class="card-body text-center">
                        <i class="fas fa-user-circle fa-3x mb-2"></i>
                        <h4>{{ patient.first_name }} {{ patient.last_name }}</h4>
                        <p class="mb-0">DOB: {{ patient.date_of_birth }}</p>
                        <p>Hospital: {{ patient.hospital }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5><i class="fas fa-heartbeat"></i> Record Vital Signs</h5>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Blood Pressure (Systolic)</label>
                                    <input type="number" name="bp_systolic" class="form-control" placeholder="e.g., 120">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Blood Pressure (Diastolic)</label>
                                    <input type="number" name="bp_diastolic" class="form-control" placeholder="e.g., 80">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-4 mb-3">
                                    <label>Heart Rate (bpm)</label>
                                    <input type="number" name="heart_rate" class="form-control" placeholder="e.g., 75">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label>Temperature (°C)</label>
                                    <input type="number" step="0.1" name="temperature" class="form-control" placeholder="e.g., 36.6">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label>Weight (kg)</label>
                                    <input type="number" step="0.1" name="weight" class="form-control" placeholder="e.g., 65.5">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Respiratory Rate</label>
                                    <input type="number" name="respiratory_rate" class="form-control" placeholder="e.g., 16">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Oxygen Saturation (%)</label>
                                    <input type="number" name="oxygen_saturation" class="form-control" placeholder="e.g., 98">
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Notes</label>
                                <textarea name="notes" class="form-control" rows="2" placeholder="Additional observations..."></textarea>
                            </div>
                            <div class="text-end">
                                <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
                                <button type="submit" class="btn btn-success">Save Vital Signs</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header bg-info text-white">
                <h5><i class="fas fa-history"></i> Vital Signs History</h5>
            </div>
            <div class="card-body">
                {% if vitals %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>BP</th>
                                <th>Heart Rate</th>
                                <th>Temp</th>
                                <th>Weight</th>
                                <th>Recorded By</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for v in vitals %}
                            <tr>
                                <td>{{ v.recorded_at.strftime('%Y-%m-%d %H:%M') if v.recorded_at else 'N/A' }}</td>
                                <td>{{ v.blood_pressure_systolic }}/{{ v.blood_pressure_diastolic }}</td>
                                <td>{{ v.heart_rate }}</td>
                                <td>{{ v.temperature }}°C</td>
                                <td>{{ v.weight }} kg</td>
                                <td>{{ v.recorded_by }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-center text-muted">No vital signs recorded yet.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
'''

APPOINTMENTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Appointments - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card bg-primary text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-user-circle fa-3x mb-2"></i>
                        <h4>{{ patient.first_name }} {{ patient.last_name }}</h4>
                        <p class="mb-0">DOB: {{ patient.date_of_birth }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5><i class="fas fa-calendar-plus"></i> Schedule Appointment</h5>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Appointment Date</label>
                                    <input type="date" name="appointment_date" class="form-control" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Appointment Time</label>
                                    <input type="time" name="appointment_time" class="form-control" required>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Doctor Name</label>
                                <input type="text" name="doctor_name" class="form-control" placeholder="e.g., Dr. Smith" required>
                            </div>
                            <div class="mb-3">
                                <label>Reason for Visit</label>
                                <textarea name="reason" class="form-control" rows="2" placeholder="Reason for appointment..."></textarea>
                            </div>
                            <div class="mb-3">
                                <label>Additional Notes</label>
                                <textarea name="notes" class="form-control" rows="2"></textarea>
                            </div>
                            <div class="text-end">
                                <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
                                <button type="submit" class="btn btn-primary">Schedule Appointment</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header bg-info text-white">
                <h5><i class="fas fa-calendar-alt"></i> Appointments History</h5>
            </div>
            <div class="card-body">
                {% if appointments %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Doctor</th>
                                <th>Reason</th>
                                <th>Status</th>
                                <th>Update</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for apt in appointments %}
                            <tr>
                                <td>{{ apt.appointment_date }}</td>
                                <td>{{ apt.appointment_time }}</td>
                                <td>{{ apt.doctor_name }}</td>
                                <td>{{ apt.reason or 'N/A' }}</td>
                                <td>
                                    {% if apt.status == 'completed' %}
                                        <span class="badge bg-success">Completed</span>
                                    {% elif apt.status == 'cancelled' %}
                                        <span class="badge bg-danger">Cancelled</span>
                                    {% else %}
                                        <span class="badge bg-primary">Scheduled</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <div class="d-flex gap-1 flex-wrap">
                                        {% if apt.status != 'completed' %}
                                        <form method="POST" action="/appointments/{{ apt.id }}/status" style="display:inline;">
                                            <input type="hidden" name="status" value="completed">
                                            <button type="submit" class="btn btn-sm btn-success">✓ Done</button>
                                        </form>
                                        {% endif %}
                                        {% if apt.status != 'cancelled' %}
                                        <form method="POST" action="/appointments/{{ apt.id }}/status" style="display:inline;">
                                            <input type="hidden" name="status" value="cancelled">
                                            <button type="submit" class="btn btn-sm btn-danger">✕ Cancel</button>
                                        </form>
                                        {% endif %}
                                        {% if apt.status != 'scheduled' %}
                                        <form method="POST" action="/appointments/{{ apt.id }}/status" style="display:inline;">
                                            <input type="hidden" name="status" value="scheduled">
                                            <button type="submit" class="btn btn-sm btn-secondary">↺ Reset</button>
                                        </form>
                                        {% endif %}
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-center text-muted">No appointments scheduled.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
'''

PREGNANCY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pregnancy Tracking - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card bg-danger text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-baby fa-3x mb-2"></i>
                        <h4>{{ patient.first_name }} {{ patient.last_name }}</h4>
                        <p class="mb-0">DOB: {{ patient.date_of_birth }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-danger text-white">
                        <h5><i class="fas fa-baby-carriage"></i> Pregnancy Record</h5>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Gravida (Number of pregnancies)</label>
                                    <input type="number" name="gravida" class="form-control" placeholder="e.g., 2">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Para (Number of births)</label>
                                    <input type="number" name="para" class="form-control" placeholder="e.g., 1">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Last Menstrual Period</label>
                                    <input type="date" name="lmp" class="form-control">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Estimated Delivery Date</label>
                                    <input type="date" name="edd" class="form-control">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Gestational Weeks</label>
                                    <input type="number" name="gestational_weeks" class="form-control" placeholder="e.g., 24">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Risk Level</label>
                                    <select name="risk_level" class="form-control">
                                        <option value="Low">Low Risk</option>
                                        <option value="Moderate">Moderate Risk</option>
                                        <option value="High">High Risk</option>
                                    </select>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Additional Notes</label>
                                <textarea name="notes" class="form-control" rows="2"></textarea>
                            </div>
                            <div class="text-end">
                                <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
                                <button type="submit" class="btn btn-danger">Save Pregnancy Record</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header bg-warning text-white">
                <h5><i class="fas fa-history"></i> Pregnancy History</h5>
            </div>
            <div class="card-body">
                {% if pregnancies %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Gravida/Para</th>
                                <th>LMP</th>
                                <th>EDD</th>
                                <th>Weeks</th>
                                <th>Risk Level</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for preg in pregnancies %}
                            <tr>
                                <td>{{ preg.recorded_at.strftime('%Y-%m-%d') if preg.recorded_at else 'N/A' }}</td>
                                <td>{{ preg.gravida }}/{{ preg.para }}</td>
                                <td>{{ preg.last_menstrual_period or 'N/A' }}</td>
                                <td>{{ preg.estimated_delivery_date or 'N/A' }}</td>
                                <td>{{ preg.gestational_weeks }} weeks</td>
                                <td><span class="badge bg-{{ 'danger' if preg.risk_level == 'High' else 'warning' if preg.risk_level == 'Moderate' else 'success' }}">{{ preg.risk_level }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-center text-muted">No pregnancy records found.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
'''

MEDICAL_HISTORY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Medical History - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .condition-card { border-left: 4px solid; margin-bottom: 15px; transition: transform 0.2s; }
        .condition-card:hover { transform: translateX(5px); }
        .status-active { border-left-color: #dc3545; background: linear-gradient(90deg, #fff0f0 0%, #ffffff 100%); }
        .status-resolved { border-left-color: #28a745; background: linear-gradient(90deg, #f0fff0 0%, #ffffff 100%); }
        .status-chronic { border-left-color: #ffc107; background: linear-gradient(90deg, #fff9e6 0%, #ffffff 100%); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card bg-info text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-user-circle fa-3x mb-2"></i>
                        <h4>{{ patient.first_name }} {{ patient.last_name }}</h4>
                        <p class="mb-0">DOB: {{ patient.date_of_birth }}</p>
                        <p>Hospital: {{ patient.hospital }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5><i class="fas fa-notes-medical"></i> Add Medical Condition</h5>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="row">
                                <div class="col-md-8 mb-3">
                                    <label>Condition / Disease Name *</label>
                                    <input type="text" name="condition_name" class="form-control" placeholder="e.g., Gestational Diabetes, Hypertension" required>
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label>Diagnosis Date</label>
                                    <input type="date" name="diagnosis_date" class="form-control">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label>Status</label>
                                    <select name="status" class="form-control">
                                        <option value="Active">Active - Under Treatment</option>
                                        <option value="Resolved">Resolved - Recovered</option>
                                        <option value="Chronic">Chronic - Long-term</option>
                                    </select>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label>Treatment Plan</label>
                                    <input type="text" name="treatment" class="form-control" placeholder="e.g., Medication, Rest">
                                </div>
                            </div>
                            <div class="mb-3">
                                <label>Medications Prescribed</label>
                                <textarea name="medications" class="form-control" rows="2" placeholder="List medications with dosage..."></textarea>
                            </div>
                            <div class="mb-3">
                                <label>Clinical Notes</label>
                                <textarea name="notes" class="form-control" rows="2"></textarea>
                            </div>
                            <div class="text-end">
                                <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
                                <button type="submit" class="btn btn-info">Save Medical Record</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header bg-primary text-white">
                <h5><i class="fas fa-history"></i> Medical History Records</h5>
            </div>
            <div class="card-body">
                {% if histories %}
                    {% for history in histories %}
                    <div class="condition-card status-{{ history.status.lower() }} card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div style="flex: 1;">
                                    <h6 class="mb-1">
                                        <i class="fas fa-stethoscope"></i>
                                        <strong>{{ history.condition_name }}</strong>
                                        {% if history.status == 'Active' %}
                                            <span class="badge bg-danger ms-2">Active</span>
                                        {% elif history.status == 'Resolved' %}
                                            <span class="badge bg-success ms-2">Resolved</span>
                                        {% else %}
                                            <span class="badge bg-warning ms-2">Chronic</span>
                                        {% endif %}
                                    </h6>
                                    <small class="text-muted">
                                        <i class="fas fa-calendar"></i> Diagnosed: {{ history.diagnosis_date or 'Date not specified' }}
                                        | <i class="fas fa-user-md"></i> Recorded by: {{ history.recorded_by }}
                                    </small>
                                    {% if history.treatment %}
                                    <p class="mt-2 mb-1"><strong>Treatment:</strong> {{ history.treatment }}</p>
                                    {% endif %}
                                    {% if history.medications %}
                                    <p class="mb-1"><strong>Medications:</strong> {{ history.medications }}</p>
                                    {% endif %}
                                    {% if history.notes %}
                                    <p class="mb-0"><strong>Notes:</strong> {{ history.notes }}</p>
                                    {% endif %}
                                </div>
                                <small class="text-muted">{{ history.recorded_at.strftime('%Y-%m-%d') if history.recorded_at else 'N/A' }}</small>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                <p class="text-center text-muted">No medical history records found.</p>
                {% endif %}
            </div>
        </div>

        <div class="mt-3 text-center">
            <a href="/patients/{{ patient.id }}" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Patient Profile
            </a>
        </div>
    </div>
</body>
</html>
'''

PATIENT_VIEW_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Patient Profile - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .card { border: none; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .info-label { font-weight: 600; color: #555; }
        .action-btn { margin: 5px; transition: transform 0.2s; cursor: pointer; }
        .action-btn:hover { transform: translateY(-5px); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-hospital-user"></i> Maternova
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/patients">Patients</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2><i class="fas fa-user-circle"></i> Patient Profile</h2>
            <div>
                <a href="/patients" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back
                </a>
                <button class="btn btn-primary" onclick="window.print()">
                    <i class="fas fa-print"></i> Print
                </button>
                <button class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#deleteModal">
                    <i class="fas fa-trash"></i> Delete Patient
                </button>
            </div>
        </div>

        <!-- Delete confirmation modal -->
        <div class="modal fade" id="deleteModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title"><i class="fas fa-exclamation-triangle"></i> Confirm Delete</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Are you sure you want to permanently delete <strong>{{ patient.first_name }} {{ patient.last_name }}</strong>?</p>
                        <p class="text-danger mb-0"><small>This will also delete all vitals, appointments, pregnancy records, and medical history for this patient. This action cannot be undone.</small></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <form method="POST" action="/patients/{{ patient.id }}/delete" style="display:inline;">
                            <button type="submit" class="btn btn-danger">Yes, Delete</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5><i class="fas fa-user"></i> Personal Information</h5>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <i class="fas fa-user-circle fa-4x text-muted"></i>
                        </div>
                        <table class="table table-sm table-borderless">
                            <tr><td class="info-label">Full Name:</td><td><strong>{{ patient.first_name }} {{ patient.last_name }}</strong></td></tr>
                            <tr><td class="info-label">Date of Birth:</td><td>{{ patient.date_of_birth }}</td></tr>
                            <tr><td class="info-label">Gender:</td><td>{{ patient.gender }}</td></tr>
                            <tr><td class="info-label">Blood Type:</td><td><span class="badge bg-danger">{{ patient.blood_type or 'Not specified' }}</span></td></tr>
                            <tr><td class="info-label">Phone:</td><td><i class="fas fa-phone"></i> {{ patient.phone or 'N/A' }}</td></tr>
                            <tr><td class="info-label">Email:</td><td><i class="fas fa-envelope"></i> {{ patient.email or 'N/A' }}</td></tr>
                            <tr><td class="info-label">Address:</td><td><i class="fas fa-map-marker-alt"></i> {{ patient.address or 'N/A' }}</td></tr>
                            <tr><td class="info-label">Allergies:</td><td><span class="text-warning">{{ patient.allergies or 'None' }}</span></td></tr>
                            <tr><td class="info-label">Hospital:</td><td>{{ patient.hospital }}</td></tr>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card bg-success text-white text-center action-btn" onclick="window.location='/vitals/{{ patient.id }}'">
                            <div class="card-body">
                                <i class="fas fa-heartbeat fa-3x mb-2"></i>
                                <h6>Vital Signs</h6>
                                <small>Record & View Vitals</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card bg-primary text-white text-center action-btn" onclick="window.location='/appointments/{{ patient.id }}'">
                            <div class="card-body">
                                <i class="fas fa-calendar-alt fa-3x mb-2"></i>
                                <h6>Appointments</h6>
                                <small>Schedule & Manage</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card bg-warning text-white text-center action-btn" onclick="window.location='/pregnancy/{{ patient.id }}'">
                            <div class="card-body">
                                <i class="fas fa-baby fa-3x mb-2"></i>
                                <h6>Pregnancy</h6>
                                <small>Track Progress</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card bg-info text-white text-center action-btn" onclick="window.location='/medical-history/{{ patient.id }}'">
                            <div class="card-body">
                                <i class="fas fa-notes-medical fa-3x mb-2"></i>
                                <h6>Medical History</h6>
                                <small>View & Add Records</small>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mt-2">
                    <div class="card-header bg-success text-white">
                        <h6><i class="fas fa-chart-line"></i> Recent Vital Signs</h6>
                    </div>
                    <div class="card-body">
                        {% if recent_vitals %}
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead><tr><th>Date</th><th>BP</th><th>HR</th><th>Temp</th><th>Weight</th></tr></thead>
                                <tbody>
                                    {% for v in recent_vitals %}
                                    <tr><td>{{ v.recorded_at.strftime('%m/%d') if v.recorded_at else 'N/A' }}</td><td>{{ v.blood_pressure_systolic }}/{{ v.blood_pressure_diastolic }}</td><td>{{ v.heart_rate }}</td><td>{{ v.temperature }}°C</td><td>{{ v.weight }}kg</td></tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                        {% else %}
                        <p class="text-muted text-center mb-0">No vital signs recorded</p>
                        {% endif %}
                    </div>
                </div>

                <div class="card mt-2">
                    <div class="card-header bg-primary text-white">
                        <h6><i class="fas fa-calendar-week"></i> Upcoming Appointments</h6>
                    </div>
                    <div class="card-body">
                        {% if upcoming_appointments %}
                        <ul class="list-unstyled mb-0">
                            {% for apt in upcoming_appointments %}
                            <li><i class="fas fa-clock"></i> {{ apt.appointment_date }} at {{ apt.appointment_time }} - Dr. {{ apt.doctor_name }}</li>
                            {% endfor %}
                        </ul>
                        {% else %}
                        <p class="text-muted text-center mb-0">No upcoming appointments</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''
ANALYTICS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Analytics - Maternova</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Fraunces:wght@600&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        body {
            background: #f5f3ef;
            font-family: 'DM Sans', sans-serif;
            color: #1a1916;
            margin: 0;
        }

        .navbar {
            background: #1a1916 !important;
            padding: 0.75rem 0;
        }
        .navbar-brand {
            font-family: 'Fraunces', serif;
            font-size: 1.25rem;
            color: #f5f3ef !important;
            letter-spacing: -0.02em;
        }
        .navbar-brand span { color: #d4a96a; }
        .nav-link {
            color: #a09e99 !important;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            transition: color 0.2s;
        }
        .nav-link:hover { color: #f5f3ef !important; }
        .nav-link.active { color: #d4a96a !important; }

        .page-header {
            padding: 2rem 0 1.5rem;
            border-bottom: 1.5px solid #e0ddd7;
            margin-bottom: 2rem;
        }
        .page-header h1 {
            font-family: 'Fraunces', serif;
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            margin: 0 0 0.2rem;
        }
        .page-header p { color: #6b6963; font-size: 0.9rem; margin: 0; }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: #fff;
            border: 1.5px solid #e0ddd7;
            border-radius: 14px;
            padding: 1.25rem 1.25rem 1rem;
            transition: border-color 0.2s;
        }
        .stat-card:hover { border-color: #c5c0b8; }
        .stat-card .icon {
            width: 34px; height: 34px;
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 15px;
            margin-bottom: 1rem;
        }
        .stat-card .val {
            font-family: 'Fraunces', serif;
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            line-height: 1;
            margin-bottom: 4px;
        }
        .stat-card .lbl {
            font-size: 0.78rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #a09e99;
        }
        .stat-card .sub {
            font-size: 0.78rem;
            color: #a09e99;
            margin-top: 6px;
        }
        .stat-card.danger  { border-left: 3px solid #a32d2d; }
        .stat-card.warning { border-left: 3px solid #854f0b; }
        .stat-card.info    { border-left: 3px solid #185fa5; }
        .stat-card.success { border-left: 3px solid #3b6d11; }

        .icon.danger  { background: #fcebeb; color: #a32d2d; }
        .icon.warning { background: #faeeda; color: #854f0b; }
        .icon.info    { background: #e6f1fb; color: #185fa5; }
        .icon.success { background: #eaf3de; color: #3b6d11; }

        .panel {
            background: #fff;
            border: 1.5px solid #e0ddd7;
            border-radius: 14px;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        .panel-head {
            padding: 1rem 1.25rem;
            border-bottom: 1.5px solid #f0ede8;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .panel-head .dot {
            width: 8px; height: 8px;
            border-radius: 50%;
        }
        .panel-head h3 {
            font-size: 0.9rem;
            font-weight: 600;
            margin: 0;
            letter-spacing: -0.01em;
        }
        .panel-body { padding: 1.25rem; }

        .flag-list { list-style: none; margin: 0; padding: 0; }
        .flag-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 0.85rem 0;
            border-bottom: 1px solid #f0ede8;
        }
        .flag-item:last-child { border-bottom: none; padding-bottom: 0; }
        .flag-item:first-child { padding-top: 0; }

        .flag-icon {
            width: 30px; height: 30px;
            border-radius: 7px;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
            margin-top: 1px;
        }
        .flag-icon.high   { background: #fcebeb; color: #a32d2d; }
        .flag-icon.medium { background: #faeeda; color: #854f0b; }
        .flag-icon.low    { background: #eaf3de; color: #3b6d11; }

        .flag-body { flex: 1; min-width: 0; }
        .flag-patient {
            font-weight: 600;
            font-size: 0.88rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .flag-reason { font-size: 0.8rem; color: #6b6963; margin-top: 2px; }
        .flag-meta   { font-size: 0.75rem; color: #a09e99; margin-top: 2px; }

        .risk-badge {
            font-size: 0.7rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 99px;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .risk-badge.high   { background: #fcebeb; color: #a32d2d; }
        .risk-badge.medium { background: #faeeda; color: #854f0b; }
        .risk-badge.low    { background: #eaf3de; color: #3b6d11; }

        .ai-panel {
            background: #1a1916;
            border-radius: 14px;
            border: 1.5px solid #2e2c28;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        .ai-panel-head {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid #2e2c28;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .ai-panel-head .ai-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #d4a96a;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .ai-panel-head h3 {
            font-size: 0.88rem;
            font-weight: 500;
            color: #a09e99;
            margin: 0;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }
        .ai-panel-head .ai-label {
            margin-left: auto;
            font-size: 0.7rem;
            padding: 2px 8px;
            border-radius: 99px;
            background: #2e2c28;
            color: #d4a96a;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .ai-panel-body { padding: 1.25rem; }
        .ai-summary-text {
            color: #c8c5bf;
            font-size: 0.9rem;
            line-height: 1.75;
            white-space: pre-wrap;
        }
        .ai-loading {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #6b6963;
            font-size: 0.88rem;
            padding: 0.5rem 0;
        }
        .ai-loading .spinner {
            width: 16px; height: 16px;
            border: 2px solid #2e2c28;
            border-top-color: #d4a96a;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .ai-actions {
            display: flex;
            gap: 8px;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #2e2c28;
        }
        .ai-btn {
            padding: 6px 14px;
            border-radius: 7px;
            font-size: 0.78rem;
            font-weight: 500;
            border: 1px solid #2e2c28;
            background: transparent;
            color: #a09e99;
            cursor: pointer;
            font-family: 'DM Sans', sans-serif;
            transition: all 0.15s;
        }
        .ai-btn:hover { background: #2e2c28; color: #f5f3ef; }
        .ai-btn.primary { background: #d4a96a; border-color: #d4a96a; color: #1a1916; font-weight: 600; }
        .ai-btn.primary:hover { background: #c49456; border-color: #c49456; }

        .chart-wrap { position: relative; width: 100%; }

        .flags-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .flags-table thead th {
            padding: 0.65rem 1rem;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: #a09e99;
            background: #faf9f6;
            border-bottom: 1.5px solid #e0ddd7;
            text-align: left;
            white-space: nowrap;
        }
        .flags-table tbody td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid #f0ede8;
            vertical-align: middle;
        }
        .flags-table tbody tr:last-child td { border-bottom: none; }
        .flags-table tbody tr:hover { background: #faf8f4; }
        .bp-val { font-weight: 600; font-size: 0.9rem; }
        .bp-val.critical { color: #a32d2d; }
        .bp-val.elevated { color: #854f0b; }
        .bp-val.normal   { color: #3b6d11; }
        .patient-link { color: #1a1916; text-decoration: none; font-weight: 600; }
        .patient-link:hover { color: #d4a96a; }

        .empty-flag {
            text-align: center;
            padding: 2.5rem 1rem;
            color: #a09e99;
            font-size: 0.88rem;
        }
        .empty-flag i { font-size: 1.5rem; margin-bottom: 0.5rem; display: block; color: #d3d1c7; }

        .two-col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) {
            .two-col { grid-template-columns: 1fr; }
        }

        .btn-refresh {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 8px 16px;
            background: #fff;
            color: #4a4843;
            border: 1.5px solid #e0ddd7;
            border-radius: 9px;
            font-family: 'DM Sans', sans-serif;
            font-size: 0.82rem;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
        }
        .btn-refresh:hover { border-color: #c5c0b8; background: #faf9f6; color: #1a1916; }

        .risk-meter { margin-bottom: 0.6rem; }
        .risk-meter-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.78rem;
            margin-bottom: 4px;
        }
        .risk-meter-label .name { font-weight: 500; color: #4a4843; }
        .risk-meter-label .pct  { color: #a09e99; }
        .risk-meter-bar {
            height: 6px;
            background: #f0ede8;
            border-radius: 99px;
            overflow: hidden;
        }
        .risk-meter-fill {
            height: 100%;
            border-radius: 99px;
            transition: width 0.6s ease;
        }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg">
    <div class="container">
        <a class="navbar-brand" href="/dashboard">Matern<span>o</span>va</a>
        <div class="navbar-nav ms-auto d-flex flex-row gap-3">
            <a class="nav-link" href="/dashboard">Dashboard</a>
            <a class="nav-link" href="/patients">Patients</a>
            <a class="nav-link active" href="/analytics">Analytics</a>
            <a class="nav-link" href="/logout">Logout</a>
        </div>
    </div>
</nav>

<div class="container">

    <div class="page-header d-flex justify-content-between align-items-start">
        <div>
            <h1>Risk Analytics</h1>
            <p>{{ current_user.hospital }} &mdash; AI-powered patient risk assessment</p>
        </div>
        <a href="/analytics" class="btn-refresh mt-2">
            <i class="fas fa-sync-alt"></i> Refresh
        </a>
    </div>

    <div class="stat-grid">
        <div class="stat-card danger">
            <div class="icon danger"><i class="fas fa-exclamation-triangle"></i></div>
            <div class="val">{{ critical_bp_count }}</div>
            <div class="lbl">Critical BP</div>
            <div class="sub">Systolic &ge; 160 mmHg</div>
        </div>
        <div class="stat-card warning">
            <div class="icon warning"><i class="fas fa-baby"></i></div>
            <div class="val">{{ high_risk_preg_count }}</div>
            <div class="lbl">High-Risk Pregnancies</div>
            <div class="sub">Flagged for close monitoring</div>
        </div>
        <div class="stat-card info">
            <div class="icon info"><i class="fas fa-users"></i></div>
            <div class="val">{{ total_patients }}</div>
            <div class="lbl">Total Patients</div>
            <div class="sub">{{ current_user.hospital }}</div>
        </div>
        <div class="stat-card success">
            <div class="icon success"><i class="fas fa-heartbeat"></i></div>
            <div class="val">{{ total_vitals }}</div>
            <div class="lbl">Vital Readings</div>
            <div class="sub">Recorded this hospital</div>
        </div>
    </div>

    <div class="ai-panel">
        <div class="ai-panel-head">
            <div class="ai-dot"></div>
            <h3>AI Risk Summary</h3>
            <span class="ai-label">Clinical AI</span>
        </div>
        <div class="ai-panel-body">
            <div id="ai-loading" class="ai-loading">
                <div class="spinner"></div>
                Analyzing patient data&hellip;
            </div>
            <div id="ai-output" class="ai-summary-text" style="display:none;"></div>
            <div class="ai-actions">
                <button class="ai-btn primary" onclick="runAISummary(false)">
                    <i class="fas fa-magic" style="font-size:11px; margin-right:4px;"></i> Generate Summary
                </button>
                <button class="ai-btn" onclick="runAISummary(true)">
                    <i class="fas fa-chart-line"></i> Detailed Report
                </button>
            </div>
        </div>
    </div>

    <div class="two-col">
        <div class="panel">
            <div class="panel-head">
                <div class="dot" style="background:#a32d2d;"></div>
                <h3>Blood pressure distribution</h3>
            </div>
            <div class="panel-body">
                <div class="chart-wrap" style="height: 220px;">
                    <canvas id="bpChart"></canvas>
                </div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-head">
                <div class="dot" style="background:#854f0b;"></div>
                <h3>Pregnancy risk levels</h3>
            </div>
            <div class="panel-body">
                {% if preg_total > 0 %}
                    <div class="risk-meter">
                        <div class="risk-meter-label">
                            <span class="name">High risk</span>
                            <span class="pct">{{ preg_high }} patients ({{ ((preg_high / preg_total) * 100)|int }}%)</span>
                        </div>
                        <div class="risk-meter-bar">
                            <div class="risk-meter-fill" style="width:{{ ((preg_high / preg_total) * 100)|int }}%; background:#a32d2d;"></div>
                        </div>
                    </div>
                    <div class="risk-meter">
                        <div class="risk-meter-label">
                            <span class="name">Moderate risk</span>
                            <span class="pct">{{ preg_moderate }} patients ({{ ((preg_moderate / preg_total) * 100)|int }}%)</span>
                        </div>
                        <div class="risk-meter-bar">
                            <div class="risk-meter-fill" style="width:{{ ((preg_moderate / preg_total) * 100)|int }}%; background:#854f0b;"></div>
                        </div>
                    </div>
                    <div class="risk-meter">
                        <div class="risk-meter-label">
                            <span class="name">Low risk</span>
                            <span class="pct">{{ preg_low }} patients ({{ ((preg_low / preg_total) * 100)|int }}%)</span>
                        </div>
                        <div class="risk-meter-bar">
                            <div class="risk-meter-fill" style="width:{{ ((preg_low / preg_total) * 100)|int }}%; background:#3b6d11;"></div>
                        </div>
                    </div>
                    <div style="margin-top:1.25rem; padding-top:1rem; border-top:1px solid #f0ede8;">
                        <span style="font-size:0.78rem; color:#a09e99; text-transform:uppercase; letter-spacing:0.06em; font-weight:600;">Total pregnancy records</span>
                        <div style="font-family:'Fraunces',serif; font-size:1.6rem; font-weight:600; letter-spacing:-0.03em; margin-top:2px;">{{ preg_total }}</div>
                    </div>
                {% else %}
                    <div class="empty-flag">
                        <i class="fas fa-baby"></i>
                        No pregnancy records found.
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="panel">
        <div class="panel-head">
            <div class="dot" style="background:#a32d2d;"></div>
            <h3>Flagged vital signs</h3>
            <span style="margin-left:auto; font-size:0.75rem; color:#a09e99;">{{ flagged_vitals|length }} records</span>
        </div>
        {% if flagged_vitals %}
        <table class="flags-table">
            <thead>
                <tr>
                    <th>Patient</th>
                    <th>BP (Sys/Dia)</th>
                    <th>Heart Rate</th>
                    <th>Temp</th>
                    <th>O&#8322; Sat</th>
                    <th>Risk Level</th>
                    <th>Recorded</th>
                </tr>
            </thead>
            <tbody>
                {% for v in flagged_vitals %}
                <tr>
                    <td>
                        <a href="/patients/{{ v.patient.id }}" class="patient-link">
                            {{ v.patient.first_name }} {{ v.patient.last_name }}
                        </a>
                    </td>
                    <td>
                        {% if v.blood_pressure_systolic and v.blood_pressure_systolic >= 160 %}
                            <span class="bp-val critical">{{ v.blood_pressure_systolic }}/{{ v.blood_pressure_diastolic }}</span>
                        {% elif v.blood_pressure_systolic and v.blood_pressure_systolic >= 140 %}
                            <span class="bp-val elevated">{{ v.blood_pressure_systolic }}/{{ v.blood_pressure_diastolic }}</span>
                        {% else %}
                            <span class="bp-val normal">{{ v.blood_pressure_systolic }}/{{ v.blood_pressure_diastolic }}</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if v.heart_rate %}
                            {% if v.heart_rate > 100 or v.heart_rate < 55 %}
                                <span style="color:#a32d2d; font-weight:600;">{{ v.heart_rate }} bpm</span>
                            {% else %}
                                {{ v.heart_rate }} bpm
                            {% endif %}
                        {% else %}—{% endif %}
                    </td>
                    <td>
                        {% if v.temperature %}
                            {% if v.temperature >= 38 %}
                                <span style="color:#a32d2d; font-weight:600;">{{ v.temperature }}°C</span>
                            {% else %}
                                {{ v.temperature }}°C
                            {% endif %}
                        {% else %}—{% endif %}
                    </td>
                    <td>
                        {% if v.oxygen_saturation %}
                            {% if v.oxygen_saturation < 95 %}
                                <span style="color:#a32d2d; font-weight:600;">{{ v.oxygen_saturation }}%</span>
                            {% else %}
                                {{ v.oxygen_saturation }}%
                            {% endif %}
                        {% else %}—{% endif %}
                    </td>
                    <td>
                        {% if v.blood_pressure_systolic and v.blood_pressure_systolic >= 160 %}
                            <span class="risk-badge high">Critical</span>
                        {% elif v.blood_pressure_systolic and v.blood_pressure_systolic >= 140 %}
                            <span class="risk-badge medium">Elevated</span>
                        {% else %}
                            <span class="risk-badge low">Monitor</span>
                        {% endif %}
                    </td>
                    <td style="color:#a09e99; font-size:0.8rem; white-space:nowrap;">
                        {{ v.recorded_at.strftime('%b %d, %Y') if v.recorded_at else '—' }}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-flag">
            <i class="fas fa-check-circle" style="color:#3b6d11;"></i>
            No flagged vital signs. All recorded readings are within normal ranges.
        </div>
        {% endif %}
    </div>

    {% if high_risk_pregnancies %}
    <div class="panel" style="margin-bottom: 2rem;">
        <div class="panel-head">
            <div class="dot" style="background:#854f0b;"></div>
            <h3>High-risk pregnancies requiring attention</h3>
            <span style="margin-left:auto; font-size:0.75rem; color:#a09e99;">{{ high_risk_pregnancies|length }} patients</span>
        </div>
        <div class="panel-body" style="padding: 0;">
            <ul class="flag-list" style="padding: 0 1.25rem;">
                {% for preg in high_risk_pregnancies %}
                <li class="flag-item">
                    <div class="flag-icon high"><i class="fas fa-baby"></i></div>
                    <div class="flag-body">
                        <div class="flag-patient">
                            <a href="/patients/{{ preg.patient_id }}" style="color:#1a1916; text-decoration:none;">
                                {{ preg.patient.first_name }} {{ preg.patient.last_name }}
                            </a>
                        </div>
                        <div class="flag-reason">
                            {{ preg.gestational_weeks or '?' }} weeks gestation
                            {% if preg.estimated_delivery_date %} &mdash; EDD: {{ preg.estimated_delivery_date }}{% endif %}
                            {% if preg.gravida %} &mdash; G{{ preg.gravida }}P{{ preg.para or 0 }}{% endif %}
                        </div>
                        {% if preg.notes %}
                        <div class="flag-meta">{{ preg.notes[:100] }}{% if preg.notes|length > 100 %}&hellip;{% endif %}</div>
                        {% endif %}
                    </div>
                    <span class="risk-badge high">High Risk</span>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
    {% endif %}

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
// BP Distribution Chart
(function() {
    const ctx = document.getElementById('bpChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Normal (<120)', 'Elevated (120-139)', 'High (140-159)', 'Critical (>=160)'],
            datasets: [{
                label: 'Patients',
                data: [{{ bp_normal }}, {{ bp_elevated }}, {{ bp_high }}, {{ bp_critical }}],
                backgroundColor: ['#3b6d11', '#854f0b', '#d4a96a', '#a32d2d'],
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.parsed.y + ' patient' + (ctx.parsed.y !== 1 ? 's' : '')
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { family: 'DM Sans', size: 11 },
                        color: '#a09e99',
                        autoSkip: false
                    }
                },
                y: {
                    grid: { color: '#f0ede8' },
                    border: { display: false },
                    ticks: {
                        font: { family: 'DM Sans', size: 11 },
                        color: '#a09e99',
                        stepSize: 1,
                        precision: 0
                    },
                    beginAtZero: true
                }
            }
        }
    });
})();

// AI Data
const AI_DATA = {
    hospital: {{ current_user.hospital | tojson }},
    total_patients: {{ total_patients }},
    total_vitals: {{ total_vitals }},
    critical_bp: {{ critical_bp_count }},
    high_risk_pregnancies: {{ high_risk_preg_count }},
    bp_normal: {{ bp_normal }},
    bp_elevated: {{ bp_elevated }},
    bp_high: {{ bp_high }},
    bp_critical: {{ bp_critical }},
    preg_high: {{ preg_high }},
    preg_moderate: {{ preg_moderate }},
    preg_low: {{ preg_low }},
    flagged_patients: [
        {% for v in flagged_vitals %}
        {
            name: {{ (v.patient.first_name + ' ' + v.patient.last_name) | tojson }},
            bp_sys: {{ v.blood_pressure_systolic or 0 }},
            bp_dia: {{ v.blood_pressure_diastolic or 0 }},
            heart_rate: {{ v.heart_rate or 0 }},
            temp: {{ v.temperature or 0 }},
            o2: {{ v.oxygen_saturation or 0 }}
        }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    high_risk_preg_patients: [
        {% for p in high_risk_pregnancies %}
        {
            name: {{ (p.patient.first_name + ' ' + p.patient.last_name) | tojson }},
            weeks: {{ p.gestational_weeks or 0 }},
            edd: {{ (p.estimated_delivery_date or '') | tojson }}
        }{% if not loop.last %},{% endif %}
        {% endfor %}
    ]
};

// Mock AI Summary - No API Key Required
function generateMockRiskReport(detailed) {
    const d = AI_DATA;
    const now = new Date();
    let report = `MATERNOVA CLINICAL RISK ASSESSMENT\n`;
    report += `${d.hospital} | ${now.toLocaleString()}\n`;
    report += `${'─'.repeat(50)}\n\n`;
    
    const totalFlags = d.critical_bp + d.high_risk_pregnancies;
    if (totalFlags === 0) {
        report += `✅ NO CRITICAL RISK FACTORS IDENTIFIED\n`;
        report += `   All monitored patients are within acceptable clinical parameters.\n\n`;
    } else if (totalFlags <= 3) {
        report += `⚠️ ${totalFlags} PATIENT(S) REQUIRE CLINICAL ATTENTION\n`;
        report += `   Priority review recommended for flagged cases below.\n\n`;
    } else {
        report += `🚨 URGENT: ${totalFlags} PATIENT(S) WITH ELEVATED RISK\n`;
        report += `   Immediate clinical review recommended.\n\n`;
    }
    
    if (d.critical_bp > 0) {
        report += `🩺 CRITICAL BLOOD PRESSURE ALERT\n`;
        report += `   • ${d.critical_bp} patient(s) with systolic BP ≥ 160 mmHg\n`;
        report += `   • Action: Evaluate for preeclampsia/hypertensive crisis\n`;
        report += `   • Recommendation: Re-check within 1 hour\n\n`;
    } else if (d.bp_high > 0) {
        report += `🩺 ELEVATED BLOOD PRESSURE\n`;
        report += `   • ${d.bp_high} patient(s) with BP 140-159 mmHg\n`;
        report += `   • Recommendation: Monitor twice daily\n\n`;
    } else {
        report += `🩺 BLOOD PRESSURE: NORMAL RANGE\n`;
        report += `   • ${d.bp_normal} patients within normal parameters\n\n`;
    }
    
    if (d.preg_high + d.preg_moderate + d.preg_low > 0) {
        report += `🤰 PREGNANCY RISK ASSESSMENT\n`;
        report += `   • High risk: ${d.preg_high} patients\n`;
        report += `   • Moderate risk: ${d.preg_moderate}\n`;
        report += `   • Low risk: ${d.preg_low}\n\n`;
    }
    
    if (detailed && d.flagged_patients.length > 0) {
        report += `🔍 DETAILED PATIENT FLAGS\n`;
        d.flagged_patients.forEach(p => {
            const issues = [];
            if (p.bp_sys >= 160) issues.push(`CRITICAL BP ${p.bp_sys}/${p.bp_dia}`);
            else if (p.bp_sys >= 140) issues.push(`elevated BP ${p.bp_sys}/${p.bp_dia}`);
            if (p.heart_rate > 100) issues.push(`tachycardia ${p.heart_rate}bpm`);
            if (p.temp >= 38) issues.push(`fever ${p.temp}°C`);
            if (p.o2 < 95 && p.o2 > 0) issues.push(`low SpO₂ ${p.o2}%`);
            if (issues.length) {
                report += `   • ${p.name}: ${issues.join(', ')}\n`;
            }
        });
        report += `\n`;
    }
    
    report += `💡 CLINICAL RECOMMENDATIONS\n`;
    if (d.critical_bp > 0) {
        report += `   1. PRIORITY: Review all ${d.critical_bp} patient(s) with critical BP\n`;
        report += `   2. Schedule repeat measurements within 24 hours\n`;
        report += `   3. Consider OB/GYN consultation for high-risk pregnancies\n`;
    } else if (d.high_risk_pregnancies > 0) {
        report += `   1. Schedule weekly monitoring for high-risk pregnancies\n`;
        report += `   2. Review medication safety profiles\n`;
        report += `   3. Coordinate with maternal-fetal medicine if available\n`;
    } else {
        report += `   1. Continue routine prenatal care schedule\n`;
        report += `   2. Maintain regular vital sign documentation\n`;
        report += `   3. Patient education on warning signs\n`;
    }
    
    report += `\n${'─'.repeat(50)}\n`;
    report += `⚠️ Clinical decision support tool. All critical findings require provider verification.`;
    
    return report;
}

function runAISummary(detailed = false) {
    const loadingEl = document.getElementById('ai-loading');
    const outputEl = document.getElementById('ai-output');
    
    loadingEl.style.display = 'flex';
    outputEl.style.display = 'none';
    
    setTimeout(() => {
        const summary = generateMockRiskReport(detailed);
        loadingEl.style.display = 'none';
        outputEl.style.display = 'block';
        outputEl.textContent = summary;
    }, 800);
}

// Auto-run on page load
runAISummary(false);
</script>

</body>
</html>
'''
# ==================== ROUTES ====================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        hospital = request.form.get('hospital')

        if password != confirm:
            flash('Passwords do not match', 'danger')
            return render_template_string(REGISTER_TEMPLATE)

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template_string(REGISTER_TEMPLATE)

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template_string(REGISTER_TEMPLATE)

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            hospital=hospital,
            role='nurse'
        )

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template_string(REGISTER_TEMPLATE)

@app.route('/dashboard')
@login_required
def dashboard():
    patients_count = Patient.query.filter_by(hospital=current_user.hospital).count()
    vitals_count = VitalSign.query.filter_by(hospital=current_user.hospital).count()
    appointments_count = Appointment.query.filter_by(hospital=current_user.hospital).count()
    pregnancies_count = PregnancyRecord.query.filter_by(hospital=current_user.hospital).count()
    recent_patients = Patient.query.filter_by(hospital=current_user.hospital).order_by(Patient.created_at.desc()).limit(5).all()

    return render_template_string(DASHBOARD_TEMPLATE,
                                 patients_count=patients_count,
                                 vitals_count=vitals_count,
                                 appointments_count=appointments_count,
                                 pregnancies_count=pregnancies_count,
                                 recent_patients=recent_patients)

@app.route('/patients')
@login_required
def list_patients():
    patients = Patient.query.filter_by(hospital=current_user.hospital).order_by(Patient.created_at.desc()).all()
    return render_template_string(PATIENTS_TEMPLATE, patients=patients)

@app.route('/patients/create', methods=['GET', 'POST'])
@login_required
def create_patient():
    if request.method == 'POST':
        try:
            patient = Patient(
                hospital=current_user.hospital,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=request.form.get('date_of_birth'),
                gender=request.form.get('gender'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                blood_type=request.form.get('blood_type'),
                allergies=request.form.get('allergies')
            )
            db.session.add(patient)
            db.session.commit()
            flash(f'Patient {patient.first_name} {patient.last_name} created successfully!', 'success')
            return redirect(url_for('list_patients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    return render_template_string(PATIENT_FORM_TEMPLATE)

@app.route('/patients/<int:patient_id>')
@login_required
def view_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    recent_vitals = VitalSign.query.filter_by(patient_id=patient_id, hospital=current_user.hospital).order_by(VitalSign.recorded_at.desc()).limit(3).all()
    upcoming_appointments = Appointment.query.filter_by(patient_id=patient_id, hospital=current_user.hospital, status='scheduled').order_by(Appointment.appointment_date).limit(3).all()

    return render_template_string(PATIENT_VIEW_TEMPLATE,
                                 patient=patient,
                                 recent_vitals=recent_vitals,
                                 upcoming_appointments=upcoming_appointments)

@app.route('/vitals/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def vitals(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    if request.method == 'POST':
        vital = VitalSign(
            patient_id=patient_id,
            hospital=current_user.hospital,
            blood_pressure_systolic=request.form.get('bp_systolic') or None,
            blood_pressure_diastolic=request.form.get('bp_diastolic') or None,
            heart_rate=request.form.get('heart_rate') or None,
            temperature=request.form.get('temperature') or None,
            weight=request.form.get('weight') or None,
            respiratory_rate=request.form.get('respiratory_rate') or None,
            oxygen_saturation=request.form.get('oxygen_saturation') or None,
            notes=request.form.get('notes'),
            recorded_by=f"{current_user.first_name} {current_user.last_name}"
        )
        db.session.add(vital)
        db.session.commit()
        flash('Vital signs recorded successfully!', 'success')
        return redirect(url_for('vitals', patient_id=patient_id))

    vitals_list = VitalSign.query.filter_by(patient_id=patient_id, hospital=current_user.hospital).order_by(VitalSign.recorded_at.desc()).all()
    return render_template_string(VITALS_FORM_TEMPLATE, patient=patient, vitals=vitals_list)

@app.route('/appointments/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def appointments(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    if request.method == 'POST':
        appointment = Appointment(
            patient_id=patient_id,
            hospital=current_user.hospital,
            appointment_date=request.form.get('appointment_date'),
            appointment_time=request.form.get('appointment_time'),
            doctor_name=request.form.get('doctor_name'),
            reason=request.form.get('reason'),
            notes=request.form.get('notes')
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment scheduled successfully!', 'success')
        return redirect(url_for('appointments', patient_id=patient_id))

    appointments_list = Appointment.query.filter_by(patient_id=patient_id, hospital=current_user.hospital).order_by(Appointment.appointment_date.desc()).all()
    return render_template_string(APPOINTMENTS_TEMPLATE, patient=patient, appointments=appointments_list)

@app.route('/pregnancy/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def pregnancy(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    if request.method == 'POST':
        preg_record = PregnancyRecord(
            patient_id=patient_id,
            hospital=current_user.hospital,
            gravida=request.form.get('gravida') or None,
            para=request.form.get('para') or None,
            last_menstrual_period=request.form.get('lmp'),
            estimated_delivery_date=request.form.get('edd'),
            gestational_weeks=request.form.get('gestational_weeks') or None,
            risk_level=request.form.get('risk_level'),
            notes=request.form.get('notes')
        )
        db.session.add(preg_record)
        db.session.commit()
        flash('Pregnancy record saved successfully!', 'success')
        return redirect(url_for('pregnancy', patient_id=patient_id))

    pregnancies_list = PregnancyRecord.query.filter_by(patient_id=patient_id, hospital=current_user.hospital).order_by(PregnancyRecord.recorded_at.desc()).all()
    return render_template_string(PREGNANCY_TEMPLATE, patient=patient, pregnancies=pregnancies_list)

@app.route('/medical-history/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def medical_history(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    if request.method == 'POST':
        history = MedicalHistory(
            patient_id=patient_id,
            hospital=current_user.hospital,
            condition_name=request.form.get('condition_name'),
            diagnosis_date=request.form.get('diagnosis_date'),
            status=request.form.get('status'),
            treatment=request.form.get('treatment'),
            medications=request.form.get('medications'),
            notes=request.form.get('notes'),
            recorded_by=f"{current_user.first_name} {current_user.last_name}"
        )
        db.session.add(history)
        db.session.commit()
        flash(f'Medical record for {history.condition_name} added successfully!', 'success')
        return redirect(url_for('medical_history', patient_id=patient_id))

    histories = MedicalHistory.query.filter_by(patient_id=patient_id, hospital=current_user.hospital).order_by(MedicalHistory.recorded_at.desc()).all()
    return render_template_string(MEDICAL_HISTORY_TEMPLATE, patient=patient, histories=histories)

@app.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
def delete_patient(patient_id):
    """Delete a patient and all their associated records."""
    patient = db.get_or_404(Patient, patient_id)
    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    name = f"{patient.first_name} {patient.last_name}"
    try:
        # Delete all related records first (FK constraints)
        VitalSign.query.filter_by(patient_id=patient_id).delete()
        Appointment.query.filter_by(patient_id=patient_id).delete()
        PregnancyRecord.query.filter_by(patient_id=patient_id).delete()
        MedicalHistory.query.filter_by(patient_id=patient_id).delete()
        db.session.delete(patient)
        db.session.commit()
        flash(f'Patient {name} and all related records have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting patient: {str(e)}', 'danger')

    return redirect(url_for('list_patients'))


@app.route('/appointments/<int:appointment_id>/status', methods=['POST'])
@login_required
def update_appointment_status(appointment_id):
    """Update appointment status (scheduled / completed / cancelled)."""
    appointment = db.get_or_404(Appointment, appointment_id)
    patient = db.get_or_404(Patient, appointment.patient_id)

    if patient.hospital != current_user.hospital:
        flash('Access denied', 'danger')
        return redirect(url_for('list_patients'))

    new_status = request.form.get('status')
    if new_status not in ('scheduled', 'completed', 'cancelled'):
        flash('Invalid status value.', 'danger')
        return redirect(url_for('appointments', patient_id=appointment.patient_id))

    appointment.status = new_status
    db.session.commit()
    flash(f'Appointment status updated to "{new_status}".', 'success')
    return redirect(url_for('appointments', patient_id=appointment.patient_id))


@app.route('/analytics')
@login_required
def analytics():
    hospital = current_user.hospital

    total_patients = Patient.query.filter_by(hospital=hospital).count()
    total_vitals   = VitalSign.query.filter_by(hospital=hospital).count()

    # Pull all vitals for BP categorization (only where systolic is recorded)
    all_vitals = VitalSign.query.filter_by(hospital=hospital)\
                    .filter(VitalSign.blood_pressure_systolic.isnot(None)).all()

    bp_normal   = sum(1 for v in all_vitals if v.blood_pressure_systolic < 120)
    bp_elevated = sum(1 for v in all_vitals if 120 <= v.blood_pressure_systolic < 140)
    bp_high     = sum(1 for v in all_vitals if 140 <= v.blood_pressure_systolic < 160)
    bp_critical = sum(1 for v in all_vitals if v.blood_pressure_systolic >= 160)

    critical_bp_count = bp_critical

    # Flagged vitals: systolic >= 140, or HR out of range, or temp >= 38, or O2 < 95
    flagged_vitals = VitalSign.query.filter_by(hospital=hospital).filter(
        db.or_(
            VitalSign.blood_pressure_systolic >= 140,
            VitalSign.heart_rate > 100,
            VitalSign.heart_rate < 55,
            VitalSign.temperature >= 38,
            VitalSign.oxygen_saturation < 95
        )
    ).order_by(VitalSign.recorded_at.desc()).all()

    # Pregnancy risk breakdown
    all_pregnancies = PregnancyRecord.query.filter_by(hospital=hospital).all()
    preg_total    = len(all_pregnancies)
    preg_high     = sum(1 for p in all_pregnancies if p.risk_level == 'High')
    preg_moderate = sum(1 for p in all_pregnancies if p.risk_level == 'Moderate')
    preg_low      = sum(1 for p in all_pregnancies if p.risk_level == 'Low')

    high_risk_preg_count = preg_high

    high_risk_pregnancies = PregnancyRecord.query.filter_by(
        hospital=hospital, risk_level='High'
    ).order_by(PregnancyRecord.recorded_at.desc()).all()

    return render_template_string(ANALYTICS_TEMPLATE,
        total_patients=total_patients,
        total_vitals=total_vitals,
        critical_bp_count=critical_bp_count,
        high_risk_preg_count=high_risk_preg_count,
        bp_normal=bp_normal,
        bp_elevated=bp_elevated,
        bp_high=bp_high,
        bp_critical=bp_critical,
        preg_total=preg_total,
        preg_high=preg_high,
        preg_moderate=preg_moderate,
        preg_low=preg_low,
        flagged_vitals=flagged_vitals,
        high_risk_pregnancies=high_risk_pregnancies,
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)