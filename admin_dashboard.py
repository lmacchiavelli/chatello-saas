#!/usr/bin/env python3
"""
Chatello SaaS Admin Dashboard
Version: 1.0.0
Author: Chatello Team
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ADMIN_SECRET_KEY', 'chatello-admin-secret-2025')

# CORS configuration
CORS(app, origins="*")

# Database configuration
DB_CONFIG = {
    'user': os.environ.get('DB_USER', 'chatello_saas'),
    'password': os.environ.get('DB_PASSWORD', 'ChatelloSaaS2025!'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'chatello_saas'),
    'raise_on_warnings': True,
    'autocommit': True
}

# Create connection pool
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="admin_pool",
        pool_size=10,
        pool_reset_session=True,
        **DB_CONFIG
    )
    print("✅ Admin Dashboard: Database pool created successfully")
except Exception as e:
    print(f"❌ Admin Dashboard: Database pool creation failed: {e}")
    db_pool = None

# Database connection decorator
def with_db_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        conn = None
        cursor = None
        try:
            conn = db_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            return f(cursor, *args, **kwargs)
        except Exception as e:
            app.logger.error(f"Database error: {e}")
            flash(f'Database error: {e}', 'error')
            return redirect(url_for('dashboard'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return decorated_function

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def dashboard():
    """Main dashboard with overview statistics"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get basic statistics
        stats = {}
        
        # Total customers
        cursor.execute("SELECT COUNT(*) as total FROM customers")
        stats['total_customers'] = cursor.fetchone()['total']
        
        # Active licenses
        cursor.execute("SELECT COUNT(*) as active FROM licenses WHERE status = 'active' AND expires_at > NOW()")
        stats['active_licenses'] = cursor.fetchone()['active']
        
        # Revenue this month
        cursor.execute("""
            SELECT SUM(amount) as revenue FROM payments 
            WHERE status = 'completed' 
            AND created_at >= DATE_FORMAT(NOW(), '%Y-%m-01')
        """)
        result = cursor.fetchone()
        stats['monthly_revenue'] = result['revenue'] if result['revenue'] else 0
        
        # API calls today
        cursor.execute("""
            SELECT COUNT(*) as calls FROM usage_logs 
            WHERE DATE(created_at) = CURDATE()
        """)
        stats['daily_api_calls'] = cursor.fetchone()['calls']
        
        # Recent licenses
        cursor.execute("""
            SELECT l.*, c.email, c.name, p.name as plan_name
            FROM licenses l
            JOIN customers c ON l.customer_id = c.id
            JOIN plans p ON l.plan_id = p.id
            ORDER BY l.created_at DESC
            LIMIT 10
        """)
        recent_licenses = cursor.fetchall()
        
        # Plan distribution
        cursor.execute("""
            SELECT p.name, COUNT(*) as count
            FROM licenses l
            JOIN plans p ON l.plan_id = p.id
            WHERE l.status = 'active' AND l.expires_at > NOW()
            GROUP BY p.name
        """)
        plan_distribution = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin/dashboard.html', 
                             stats=stats, 
                             recent_licenses=recent_licenses,
                             plan_distribution=plan_distribution)
        
    except Exception as e:
        flash(f'Database error: {e}', 'error')
        return render_template('admin/dashboard.html', stats={}, recent_licenses=[], plan_distribution=[])

@app.route('/customers')
@login_required
def customers():
    """Customer management page"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all customers with their license info
        cursor.execute("""
            SELECT c.*, 
                   COUNT(l.id) as total_licenses,
                   SUM(CASE WHEN l.status = 'active' AND l.expires_at > NOW() THEN 1 ELSE 0 END) as active_licenses
            FROM customers c
            LEFT JOIN licenses l ON c.id = l.customer_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """)
        customers_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin/customers.html', customers=customers_list)
        
    except Exception as e:
        flash(f'Database error: {e}', 'error')
        return render_template('admin/customers.html', customers=[])

@app.route('/licenses')
@login_required
def licenses():
    """License management page"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all licenses with customer and plan info
        cursor.execute("""
            SELECT l.*, c.email, c.name as customer_name, p.name as plan_name, p.price
            FROM licenses l
            JOIN customers c ON l.customer_id = c.id
            JOIN plans p ON l.plan_id = p.id
            ORDER BY l.created_at DESC
        """)
        licenses_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin/licenses.html', licenses=licenses_list)
        
    except Exception as e:
        flash(f'Database error: {e}', 'error')
        return render_template('admin/licenses.html', licenses=[])

@app.route('/usage')
@login_required
def usage():
    """Usage analytics page"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Daily usage for last 30 days
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as requests, SUM(tokens_used) as tokens
            FROM usage_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        daily_usage = cursor.fetchall()
        
        # Usage by provider
        cursor.execute("""
            SELECT endpoint as provider, COUNT(*) as requests, SUM(tokens_used) as tokens
            FROM usage_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY endpoint
            ORDER BY requests DESC
        """)
        provider_usage = cursor.fetchall()
        
        # Top licenses by usage
        cursor.execute("""
            SELECT l.license_key, c.email, COUNT(*) as requests, SUM(ul.tokens_used) as tokens
            FROM usage_logs ul
            JOIN licenses l ON ul.license_id = l.id
            JOIN customers c ON l.customer_id = c.id
            WHERE ul.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY l.id
            ORDER BY requests DESC
            LIMIT 20
        """)
        top_licenses = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin/usage.html', 
                             daily_usage=daily_usage,
                             provider_usage=provider_usage,
                             top_licenses=top_licenses)
        
    except Exception as e:
        flash(f'Database error: {e}', 'error')
        return render_template('admin/usage.html', daily_usage=[], provider_usage=[], top_licenses=[])

@app.route('/create_license', methods=['GET', 'POST'])
@login_required
def create_license():
    """Create new license"""
    if request.method == 'POST':
        try:
            conn = db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get form data
            customer_email = request.form['customer_email']
            plan_id = request.form['plan_id']
            duration_months = int(request.form['duration_months'])
            
            # Check if customer exists, create if not
            cursor.execute("SELECT id FROM customers WHERE email = %s", (customer_email,))
            customer = cursor.fetchone()
            
            if not customer:
                # Create new customer
                cursor.execute("""
                    INSERT INTO customers (email, name, created_at)
                    VALUES (%s, %s, NOW())
                """, (customer_email, customer_email.split('@')[0]))
                customer_id = cursor.lastrowid
            else:
                customer_id = customer[0]
            
            # Generate license key
            import secrets
            license_key = f"CHA-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
            
            # Calculate expiration
            expires_at = datetime.now() + timedelta(days=duration_months * 30)
            
            # Create license
            cursor.execute("""
                INSERT INTO licenses (license_key, customer_id, plan_id, status, expires_at, created_at)
                VALUES (%s, %s, %s, 'active', %s, NOW())
            """, (license_key, customer_id, plan_id, expires_at))
            
            cursor.close()
            conn.close()
            
            flash(f'License created successfully: {license_key}', 'success')
            return redirect(url_for('licenses'))
            
        except Exception as e:
            flash(f'Error creating license: {e}', 'error')
    
    # Get plans for form
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM plans ORDER BY price")
        plans = cursor.fetchall()
        cursor.close()
        conn.close()
    except:
        plans = []
    
    return render_template('admin/create_license.html', plans=plans)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple authentication (in production, use proper authentication)
        if username == 'admin' and password == 'ChatelloAdmin2025!':
            session['logged_in'] = True
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.pop('logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# API endpoints for AJAX requests
@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard stats"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Real-time stats
        stats = {}
        
        # API calls in last hour
        cursor.execute("""
            SELECT COUNT(*) as calls FROM usage_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        stats['hourly_calls'] = cursor.fetchone()['calls']
        
        # Revenue today
        cursor.execute("""
            SELECT SUM(amount) as revenue FROM payments 
            WHERE status = 'completed' 
            AND DATE(created_at) = CURDATE()
        """)
        result = cursor.fetchone()
        stats['daily_revenue'] = float(result['revenue']) if result['revenue'] else 0.0
        
        cursor.close()
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle_license/<int:license_id>')
@login_required
def toggle_license(license_id):
    """Toggle license status"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get current status
        cursor.execute("SELECT status FROM licenses WHERE id = %s", (license_id,))
        current = cursor.fetchone()
        
        if not current:
            return jsonify({'error': 'License not found'}), 404
        
        # Toggle status
        new_status = 'suspended' if current['status'] == 'active' else 'active'
        cursor.execute("UPDATE licenses SET status = %s WHERE id = %s", (new_status, license_id))
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'new_status': new_status})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Customer API endpoints
@app.route('/api/customer/<int:customer_id>')
@login_required
def get_customer(customer_id):
    """Get customer details by ID"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get customer info
        cursor.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT l.id) as total_licenses,
                   COUNT(DISTINCT CASE WHEN l.status = 'active' THEN l.id END) as active_licenses
            FROM customers c
            LEFT JOIN licenses l ON c.id = l.customer_id
            WHERE c.id = %s
            GROUP BY c.id
        """, (customer_id,))
        
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer's licenses
        cursor.execute("""
            SELECT l.*, p.name as plan_name
            FROM licenses l
            JOIN plans p ON l.plan_id = p.id
            WHERE l.customer_id = %s
            ORDER BY l.created_at DESC
        """, (customer_id,))
        
        licenses = cursor.fetchall()
        
        # Convert datetime objects to strings
        if customer.get('created_at'):
            customer['created_at'] = customer['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        for license in licenses:
            if license.get('created_at'):
                license['created_at'] = license['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if license.get('expires_at'):
                license['expires_at'] = license['expires_at'].strftime('%Y-%m-%d')
        
        customer['licenses'] = licenses
        
        cursor.close()
        conn.close()
        
        return jsonify(customer)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer/<int:customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    """Update customer details"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if customer exists
        cursor.execute("SELECT id FROM customers WHERE id = %s", (customer_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        if 'name' in data:
            update_fields.append("name = %s")
            update_values.append(data['name'])
        
        if 'email' in data:
            update_fields.append("email = %s")
            update_values.append(data['email'])
        
        if 'company' in data:
            update_fields.append("company = %s")
            update_values.append(data['company'])
        
        if 'notes' in data:
            update_fields.append("notes = %s")
            update_values.append(data['notes'])
        
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Add customer_id to values for WHERE clause
        update_values.append(customer_id)
        
        # Execute update
        query = f"UPDATE customers SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, update_values)
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Customer updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer', methods=['POST'])
@login_required
def create_customer():
    """Create new customer"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
        
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if email already exists
        cursor.execute("SELECT id FROM customers WHERE email = %s", (data['email'],))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Email already exists'}), 400
        
        # Insert new customer
        cursor.execute("""
            INSERT INTO customers (email, name, company, notes, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            data['email'],
            data.get('name', ''),
            data.get('company', ''),
            data.get('notes', '')
        ))
        
        customer_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'customer_id': customer_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    """Delete customer and all associated data"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if customer exists
        cursor.execute("SELECT id FROM customers WHERE id = %s", (customer_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Delete in order: usage_logs -> licenses -> api_keys -> payments -> customer
        cursor.execute("DELETE ul FROM usage_logs ul JOIN licenses l ON ul.license_id = l.id WHERE l.customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM licenses WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM api_keys WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM payments WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Customer deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5012, debug=True)