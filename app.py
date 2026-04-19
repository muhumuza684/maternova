"""
Empirical Investigation System
Based on SENG 421: Software Metrics - Chapter 4
University of Calgary - B.H. Far
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'empirical-investigation-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///empirical.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class User(UserMixin, db.Model):
    """Researcher / investigator user account."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    investigations = db.relationship('Investigation', backref='researcher', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Investigation(db.Model):
    """
    Core entity: an empirical SE investigation.
    Covers Chapter 4 concepts: hypothesis, technique, variables, guidelines.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    # SE Investigation metadata
    purpose = db.Column(db.String(50), nullable=False)          # improve | evaluate | prove | disprove | understand | compare
    technique = db.Column(db.String(50), nullable=False)        # formal_experiment | case_study | survey
    context = db.Column(db.String(50), nullable=False)          # field | lab | classroom
    hypothesis = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    # Experimental design fields (Guidelines Section 2)
    population = db.Column(db.Text)
    selection_criteria = db.Column(db.Text)
    assignment_process = db.Column(db.Text)
    sample_size = db.Column(db.Integer)
    outcome_measures = db.Column(db.Text)

    # Status tracking
    status = db.Column(db.String(30), default='conception')     # conception | design | preparation | execution | review | dissemination
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    variables = db.relationship('Variable', backref='investigation', lazy=True, cascade='all, delete-orphan')
    data_points = db.relationship('DataPoint', backref='investigation', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='investigation', lazy=True, cascade='all, delete-orphan')


class Variable(db.Model):
    """
    Independent / dependent / confounding variable for an investigation.
    Implements Control principle from Chapter 4.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    var_type = db.Column(db.String(20), nullable=False)         # independent | dependent | confounding
    description = db.Column(db.Text)
    unit = db.Column(db.String(50))
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigation.id'), nullable=False)


class DataPoint(db.Model):
    """
    A single collected data observation.
    Supports Guidelines Section 3: Data Collection (DC1–DC4).
    """
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.String(50), nullable=False)       # anonymised participant/object ID
    variable_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    treatment_group = db.Column(db.String(100))
    block_group = db.Column(db.String(100))                     # blocking support
    dropped_out = db.Column(db.Boolean, default=False)          # DC3: record drop-outs
    notes = db.Column(db.Text)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigation.id'), nullable=False)


class Result(db.Model):
    """
    Analysis result / conclusion for an investigation.
    Implements Guidelines Sections 4–6: Analysis, Presentation, Interpretation.
    """
    id = db.Column(db.Integer, primary_key=True)
    finding = db.Column(db.Text, nullable=False)
    statistical_significance = db.Column(db.Float)              # p-value
    practical_importance = db.Column(db.Text)                   # I2: distinguish from significance
    limitations = db.Column(db.Text)                            # I3
    hypothesis_confirmed = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigation.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
# ROUTES — Auth
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# ROUTES — Dashboard
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    investigations = Investigation.query.filter_by(user_id=current_user.id)\
        .order_by(Investigation.updated_at.desc()).all()

    stats = {
        'total': len(investigations),
        'by_technique': {},
        'by_status': {},
    }
    for inv in investigations:
        stats['by_technique'][inv.technique] = stats['by_technique'].get(inv.technique, 0) + 1
        stats['by_status'][inv.status] = stats['by_status'].get(inv.status, 0) + 1

    return render_template('dashboard.html', investigations=investigations, stats=stats)


# ─────────────────────────────────────────────
# ROUTES — Investigations CRUD
# ─────────────────────────────────────────────

@app.route('/investigations/new', methods=['GET', 'POST'])
@login_required
def new_investigation():
    if request.method == 'POST':
        inv = Investigation(
            title=request.form['title'],
            purpose=request.form['purpose'],
            technique=request.form['technique'],
            context=request.form['context'],
            hypothesis=request.form['hypothesis'],
            description=request.form.get('description', ''),
            population=request.form.get('population', ''),
            selection_criteria=request.form.get('selection_criteria', ''),
            assignment_process=request.form.get('assignment_process', ''),
            sample_size=int(request.form['sample_size']) if request.form.get('sample_size') else None,
            outcome_measures=request.form.get('outcome_measures', ''),
            user_id=current_user.id,
        )
        db.session.add(inv)
        db.session.commit()
        flash('Investigation created!', 'success')
        return redirect(url_for('view_investigation', inv_id=inv.id))

    return render_template('investigation_form.html', action='New', inv=None)


@app.route('/investigations/<int:inv_id>')
@login_required
def view_investigation(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    causal_order = _compute_causal_order(inv.variables)
    return render_template('investigation_detail.html', inv=inv, causal_order=causal_order)


@app.route('/investigations/<int:inv_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_investigation(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        inv.title = request.form['title']
        inv.purpose = request.form['purpose']
        inv.technique = request.form['technique']
        inv.context = request.form['context']
        inv.hypothesis = request.form['hypothesis']
        inv.description = request.form.get('description', '')
        inv.population = request.form.get('population', '')
        inv.selection_criteria = request.form.get('selection_criteria', '')
        inv.assignment_process = request.form.get('assignment_process', '')
        inv.sample_size = int(request.form['sample_size']) if request.form.get('sample_size') else None
        inv.outcome_measures = request.form.get('outcome_measures', '')
        inv.status = request.form.get('status', inv.status)
        db.session.commit()
        flash('Investigation updated!', 'success')
        return redirect(url_for('view_investigation', inv_id=inv.id))

    return render_template('investigation_form.html', action='Edit', inv=inv)


@app.route('/investigations/<int:inv_id>/delete', methods=['POST'])
@login_required
def delete_investigation(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    flash('Investigation deleted.', 'info')
    return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────
# ROUTES — Variables
# ─────────────────────────────────────────────

@app.route('/investigations/<int:inv_id>/variables/add', methods=['POST'])
@login_required
def add_variable(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    var = Variable(
        name=request.form['name'],
        var_type=request.form['var_type'],
        description=request.form.get('description', ''),
        unit=request.form.get('unit', ''),
        investigation_id=inv.id,
    )
    db.session.add(var)
    db.session.commit()
    flash(f'Variable "{var.name}" added.', 'success')
    return redirect(url_for('view_investigation', inv_id=inv_id))


@app.route('/variables/<int:var_id>/delete', methods=['POST'])
@login_required
def delete_variable(var_id):
    var = Variable.query.get_or_404(var_id)
    inv = Investigation.query.filter_by(id=var.investigation_id, user_id=current_user.id).first_or_404()
    db.session.delete(var)
    db.session.commit()
    flash('Variable removed.', 'info')
    return redirect(url_for('view_investigation', inv_id=inv.id))


# ─────────────────────────────────────────────
# ROUTES — Data Collection
# ─────────────────────────────────────────────

@app.route('/investigations/<int:inv_id>/data/add', methods=['POST'])
@login_required
def add_data_point(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    dp = DataPoint(
        subject_id=request.form['subject_id'],
        variable_name=request.form['variable_name'],
        value=float(request.form['value']),
        treatment_group=request.form.get('treatment_group', ''),
        block_group=request.form.get('block_group', ''),
        dropped_out=request.form.get('dropped_out') == 'on',
        notes=request.form.get('notes', ''),
        investigation_id=inv.id,
    )
    db.session.add(dp)
    db.session.commit()
    flash('Data point recorded.', 'success')
    return redirect(url_for('view_investigation', inv_id=inv_id))


@app.route('/data/<int:dp_id>/delete', methods=['POST'])
@login_required
def delete_data_point(dp_id):
    dp = DataPoint.query.get_or_404(dp_id)
    inv = Investigation.query.filter_by(id=dp.investigation_id, user_id=current_user.id).first_or_404()
    db.session.delete(dp)
    db.session.commit()
    flash('Data point removed.', 'info')
    return redirect(url_for('view_investigation', inv_id=inv.id))


# ─────────────────────────────────────────────
# ROUTES — Results & Analysis
# ─────────────────────────────────────────────

@app.route('/investigations/<int:inv_id>/results/add', methods=['POST'])
@login_required
def add_result(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    result = Result(
        finding=request.form['finding'],
        statistical_significance=float(request.form['statistical_significance']) if request.form.get('statistical_significance') else None,
        practical_importance=request.form.get('practical_importance', ''),
        limitations=request.form.get('limitations', ''),
        hypothesis_confirmed=request.form.get('hypothesis_confirmed') == 'yes',
        investigation_id=inv.id,
    )
    db.session.add(result)
    db.session.commit()
    flash('Result recorded.', 'success')
    return redirect(url_for('view_investigation', inv_id=inv_id))


@app.route('/results/<int:result_id>/delete', methods=['POST'])
@login_required
def delete_result(result_id):
    result = Result.query.get_or_404(result_id)
    inv = Investigation.query.filter_by(id=result.investigation_id, user_id=current_user.id).first_or_404()
    db.session.delete(result)
    db.session.commit()
    flash('Result removed.', 'info')
    return redirect(url_for('view_investigation', inv_id=inv.id))


# ─────────────────────────────────────────────
# ROUTES — API (JSON)
# ─────────────────────────────────────────────

@app.route('/api/investigations')
@login_required
def api_investigations():
    investigations = Investigation.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': i.id,
        'title': i.title,
        'technique': i.technique,
        'status': i.status,
        'hypothesis': i.hypothesis[:80] + '...' if len(i.hypothesis) > 80 else i.hypothesis,
    } for i in investigations])


@app.route('/api/investigations/<int:inv_id>/summary')
@login_required
def api_investigation_summary(inv_id):
    inv = Investigation.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    data_points = DataPoint.query.filter_by(investigation_id=inv_id, dropped_out=False).all()

    values_by_var = {}
    for dp in data_points:
        values_by_var.setdefault(dp.variable_name, []).append(dp.value)

    summary = {}
    for var_name, vals in values_by_var.items():
        n = len(vals)
        mean = sum(vals) / n if n else 0
        summary[var_name] = {
            'n': n,
            'mean': round(mean, 4),
            'min': min(vals),
            'max': max(vals),
        }

    return jsonify({
        'id': inv.id,
        'title': inv.title,
        'technique': inv.technique,
        'status': inv.status,
        'variable_count': len(inv.variables),
        'data_point_count': len(data_points),
        'result_count': len(inv.results),
        'data_summary': summary,
    })


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _compute_causal_order(variables):
    """
    Simple causal ordering display for dependent/independent variables.
    Based on Chapter 4: Control /3 — causal ordering {A,B,C} => {D} => {F} => {Z}
    """
    independent = [v for v in variables if v.var_type == 'independent']
    dependent = [v for v in variables if v.var_type == 'dependent']
    confounding = [v for v in variables if v.var_type == 'confounding']

    order = []
    if independent:
        order.append({'label': 'Independent (Given)', 'vars': independent, 'arrow': True})
    if confounding:
        order.append({'label': 'Confounding', 'vars': confounding, 'arrow': True})
    if dependent:
        order.append({'label': 'Dependent (Outcome)', 'vars': dependent, 'arrow': False})
    return order


# ─────────────────────────────────────────────
# TEMPLATE FILTERS
# ─────────────────────────────────────────────

@app.template_filter('technique_label')
def technique_label(t):
    return {'formal_experiment': 'Formal Experiment', 'case_study': 'Case Study', 'survey': 'Survey'}.get(t, t)


@app.template_filter('purpose_label')
def purpose_label(p):
    labels = {
        'improve': 'Improve', 'evaluate': 'Evaluate', 'prove': 'Prove',
        'disprove': 'Disprove', 'understand': 'Understand', 'compare': 'Compare',
    }
    return labels.get(p, p)


@app.template_filter('status_label')
def status_label(s):
    labels = {
        'conception': 'Conception', 'design': 'Design', 'preparation': 'Preparation',
        'execution': 'Execution', 'review': 'Review & Analysis', 'dissemination': 'Dissemination',
    }
    return labels.get(s, s)


# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────

def create_tables():
    with app.app_context():
        db.create_all()
        # Seed demo user if DB is fresh
        if not User.query.filter_by(username='demo').first():
            demo = User(username='demo', email='demo@example.com')
            demo.set_password('demo1234')
            db.session.add(demo)
            db.session.commit()


if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
