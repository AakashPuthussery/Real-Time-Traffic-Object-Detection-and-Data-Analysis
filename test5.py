from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a random string in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:12345678@localhost/traffic_db'  # Replace with your database credentials
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Create all tables
def initialize_db():
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                username='admin',
                full_name='System Administrator',
                role='admin',
                status='approved'
            )
            admin.set_password('admin123')  # Change this in production
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return render_template('login.html')
            
        if user.status != 'approved' and user.role != 'admin':
            if user.status == 'pending':
                flash('Your account is pending approval', 'warning')
            else:
                flash('Your account has been rejected', 'error')
            return render_template('login.html')
            
        session['user_id'] = user.id
        
        # Redirect to index.html instead of dashboard
        return redirect(url_for('index_page'))
            
    return render_template('login.html')

@app.route('/index')
def index_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         email = request.form['email']
#         full_name = request.form['fullName']
#         role = request.form['role']
#         password = request.form['password']
        
#         # Generate username from email
#         username = email.split('@')[0]
        
#         # Check if email already exists
#         existing_user = User.query.filter_by(email=email).first()
#         if existing_user:
#             flash('Email already registered', 'error')
#             return render_template('signup.html')
            
#         # Create new user
#         new_user = User(
#             email=email,
#             username=username,
#             full_name=full_name,
#             role=role
#         )
#         new_user.set_password(password)
        
#         # Set status based on role
#         if role in ['Police Officer', 'RTO', 'Government Official']:
#             new_user.status = 'pending'
#         else:
#             new_user.status = 'approved'
            
#         db.session.add(new_user)
#         db.session.commit()
        
#         # If AJAX request, return JSON response
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return jsonify({'success': True, 'message': 'Account created successfully'})
            
#         flash('Account created successfully!', 'success')
#         return redirect(url_for('login'))
        
#     return render_template('signup.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            full_name = request.form.get('fullName')
            role = request.form.get('role')
            password = request.form.get('password')

            # Debugging Prints
            print(f"Received: email={email}, full_name={full_name}, role={role}")

            if not email or not full_name or not role or not password:
                flash('All fields are required', 'error')
                return render_template('signup.html')

            # Generate username
            username = email.split('@')[0]
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('signup.html')

            # Create new user
            new_user = User(
                email=email,
                username=username,
                full_name=full_name,
                role=role
            )
            new_user.set_password(password)

            # Set status based on role
            new_user.status = 'pending' if role in ['Police Officer', 'RTO', 'Government Official'] else 'approved'

            # Insert into database
            db.session.add(new_user)
            db.session.commit()
            print("User created successfully!")

            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print("Error during signup:", str(e))
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
        
    # Get all pending users that need approval
    pending_users = User.query.filter(
        User.status == 'pending',
        User.role.in_(['Police Officer', 'RTO', 'Government Official'])
    ).all()
    
    # Get recently approved users
    approved_users = User.query.filter(
        User.status == 'approved',
        User.role.in_(['Police Officer', 'RTO', 'Government Official'])
    ).order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin.html', pending_users=pending_users, approved_users=approved_users)

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
        
    admin = User.query.get(session['user_id'])
    if not admin or admin.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
        
    user.status = 'approved'
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'User {user.full_name} has been approved'
    })

@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
        
    admin = User.query.get(session['user_id'])
    if not admin or admin.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
        
    user.status = 'rejected'
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'User {user.full_name} has been rejected'
    })

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    # This would be a basic dashboard for regular users
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password():
    # This would be implemented with email functionality
    return render_template('forgot_password.html')

if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)