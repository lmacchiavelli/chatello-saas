#!/usr/bin/env python3
"""
Chatello SaaS Admin Dashboard
License and customer management interface
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import mysql.connector
from mysql.connector import pooling
import hashlib
import secrets
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ADMIN_SECRET_KEY', secrets.token_hex(32))

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database configuration
DB_CONFIG = {
    'user': 'chatello_saas',
    'password': 'ChatelloSaaS2025!',
    'host': 'localhost',
    'database': 'chatello_saas',
    'pool_name': 'admin_pool',
    'pool_size': 5
}

# Create connection pool
db_pool = pooling.MySQLConnectionPool(**DB_CONFIG)

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    # Simple admin user (in production, use database)
    if user_id == "admin":
        return User("admin", "admin")
    return None

def get_db():
    return db_pool.get_connection()

@app.route('/')
@login_required
def dashboard():
    """Main dashboard with statistics"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get statistics
    stats = {}
    
    # Total customers
    cursor.execute("SELECT COUNT(*) as total FROM customers WHERE status = 'active'")
    stats['customers'] = cursor.fetchone()['total']
    
    # Total active licenses
    cursor.execute("SELECT COUNT(*) as total FROM licenses WHERE status = 'active'")
    stats['licenses'] = cursor.fetchone()['total']
    
    # Revenue this month
    cursor.execute("""
        SELECT SUM(amount) as total 
        FROM payments 
        WHERE status = 'completed' 
        AND MONTH(created_at) = MONTH(CURRENT_DATE())
    """)
    stats['revenue'] = cursor.fetchone()['total'] or 0
    
    # API calls this month
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM usage_logs 
        WHERE MONTH(created_at) = MONTH(CURRENT_DATE())
    """)
    stats['api_calls'] = cursor.fetchone()['total']
    
    # Recent activity
    cursor.execute("""
        SELECT l.*, c.email, c.name, p.display_name as plan_name
        FROM licenses l
        JOIN customers c ON l.customer_id = c.id
        JOIN plans p ON l.plan_id = p.id
        ORDER BY l.created_at DESC
        LIMIT 10
    """)
    recent_licenses = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template('dashboard.html', stats=stats, recent_licenses=recent_licenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication (in production, use proper auth)
        if username == 'admin' and password == 'ChatelloAdmin2025!':
            user = User('admin', 'admin')
            login_user(user)
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/licenses')
@login_required
def licenses():
    """License management page"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get all licenses with customer and plan info
    cursor.execute("""
        SELECT l.*, c.email, c.name, c.company, p.display_name as plan_name
        FROM licenses l
        JOIN customers c ON l.customer_id = c.id
        JOIN plans p ON l.plan_id = p.id
        ORDER BY l.created_at DESC
    """)
    licenses = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template('licenses.html', licenses=licenses)

@app.route('/customers')
@login_required
def customers():
    """Customer management page"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get all customers with license count
    cursor.execute("""
        SELECT c.*, COUNT(l.id) as license_count
        FROM customers c
        LEFT JOIN licenses l ON c.id = l.customer_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """)
    customers = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template('customers.html', customers=customers)

@app.route('/api/create_license', methods=['POST'])
@login_required
def create_license():
    """Create new license"""
    data = request.get_json()
    
    email = data.get('email')
    name = data.get('name')
    domain = data.get('domain')
    plan_id = data.get('plan_id')
    
    if not all([email, plan_id]):
        return jsonify({'error': 'Missing required fields: email and plan_id'}), 400
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Check if customer exists
        cursor.execute("SELECT id FROM customers WHERE email = %s", (email,))
        customer = cursor.fetchone()
        
        if not customer:
            # Create new customer
            cursor.execute("""
                INSERT INTO customers (email, name, status)
                VALUES (%s, %s, 'active')
            """, (email, name))
            customer_id = cursor.lastrowid
        else:
            customer_id = customer['id']
        
        # Generate license key
        cursor.callproc('generate_license_key', [customer_id, plan_id, domain or None])
        
        # Get the generated license key
        for result in cursor.stored_results():
            license_key = result.fetchone()[0]
        
        db.commit()
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'customer_id': customer_id
        })
        
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/toggle_license/<int:license_id>', methods=['POST'])
@login_required
def toggle_license(license_id):
    """Toggle license status"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get current status
        cursor.execute("SELECT status FROM licenses WHERE id = %s", (license_id,))
        current_status = cursor.fetchone()[0]
        
        # Toggle status
        new_status = 'inactive' if current_status == 'active' else 'active'
        cursor.execute("""
            UPDATE licenses 
            SET status = %s 
            WHERE id = %s
        """, (new_status, license_id))
        
        db.commit()
        
        return jsonify({'success': True, 'new_status': new_status})
        
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/usage/<int:license_id>')
@login_required
def get_usage(license_id):
    """Get usage statistics for a license"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get daily usage for last 30 days
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as requests,
            SUM(tokens_used) as tokens
        FROM usage_logs
        WHERE license_id = %s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """, (license_id,))
    
    usage_data = cursor.fetchall()
    
    # Convert dates to strings
    for row in usage_data:
        row['date'] = row['date'].isoformat()
    
    cursor.close()
    db.close()
    
    return jsonify(usage_data)

@app.route('/api/stats')
@login_required
def get_stats():
    """Get dashboard statistics"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    stats = {}
    
    # Plans distribution
    cursor.execute("""
        SELECT p.display_name, COUNT(l.id) as count
        FROM plans p
        LEFT JOIN licenses l ON p.id = l.plan_id AND l.status = 'active'
        GROUP BY p.id
    """)
    stats['plans'] = cursor.fetchall()
    
    # Monthly revenue trend
    cursor.execute("""
        SELECT 
            DATE_FORMAT(created_at, '%Y-%m') as month,
            SUM(amount) as revenue
        FROM payments
        WHERE status = 'completed'
        AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month
    """)
    stats['revenue_trend'] = cursor.fetchall()
    
    # API usage trend
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as calls
        FROM usage_logs
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    stats['api_trend'] = cursor.fetchall()
    
    # Convert dates to strings
    for row in stats['api_trend']:
        row['date'] = row['date'].isoformat()
    
    cursor.close()
    db.close()
    
    return jsonify(stats)

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5011)