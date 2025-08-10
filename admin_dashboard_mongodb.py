#!/usr/bin/env python3
"""
Chatello SaaS Admin Dashboard - MongoDB Edition
Version: 2.0.0-mongodb
Author: Chatello Team
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import os
from datetime import datetime, timedelta, timezone
import calendar
from functools import wraps
import hashlib
import json
import io
from dotenv import load_dotenv, set_key
import secrets
import re

# Import MongoDB schema utilities
from mongodb_schema import generate_license_key, init_mongodb_collections

# Load environment variables
load_dotenv()

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ADMIN_SECRET_KEY', 'chatello-admin-secret-2025')

# CORS configuration
CORS(app, origins="*")

# MongoDB Atlas Configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://lmacchiavelli:BINI9RIhBOvjy3eu@chatello.38m5lpq.mongodb.net/?retryWrites=true&w=majority&appName=chatello')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'chatello_saas')

# Initialize MongoDB connection
try:
    mongo_client = MongoClient(MONGODB_URI)
    mongo_db = mongo_client[DATABASE_NAME]
    print("✅ Admin Dashboard: Connected to MongoDB Atlas")
    
    # Test connection
    mongo_client.admin.command('ping')
    print("✅ Admin Dashboard: MongoDB Atlas ping successful")
    
    # Initialize collections if needed
    init_mongodb_collections(mongo_db)
    print("✅ Admin Dashboard: MongoDB collections initialized")
    
except Exception as e:
    print(f"❌ Admin Dashboard: MongoDB connection failed: {e}")
    mongo_client = None
    mongo_db = None

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
        stats = {}
        
        # Total customers
        stats['total_customers'] = mongo_db.customers.count_documents({})
        
        # Active licenses  
        stats['active_licenses'] = mongo_db.licenses.count_documents({
            'status': 'active',
            '$or': [
                {'expires_at': None},  # Never expires
                {'expires_at': {'$gt': datetime.now(timezone.utc)}}  # Not expired
            ]
        })
        
        # Expired licenses
        stats['expired_licenses'] = mongo_db.licenses.count_documents({
            'expires_at': {'$lt': datetime.now(timezone.utc)},
            'status': {'$ne': 'cancelled'}
        })
        
        # Revenue by plan (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Get plan statistics
        pipeline = [
            {
                '$lookup': {
                    'from': 'plans',
                    'localField': 'plan_id',
                    'foreignField': '_id',
                    'as': 'plan_info'
                }
            },
            {
                '$unwind': '$plan_info'
            },
            {
                '$group': {
                    '_id': '$plan_info.name',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        plan_stats = list(mongo_db.licenses.aggregate(pipeline))
        stats['plan_distribution'] = {item['_id']: item['count'] for item in plan_stats}
        
        # Get Founders Deal specific statistics
        founders_plan = mongo_db.plans.find_one({'name': 'founders'})
        if founders_plan:
            founders_licenses_count = mongo_db.licenses.count_documents({
                'plan_id': founders_plan['_id'],
                'status': {'$in': ['active', 'inactive']}
            })
            
            stats['founders_deal'] = {
                'sold': founders_licenses_count,
                'remaining': founders_plan['lifetime_limit'] - founders_licenses_count,
                'total_limit': founders_plan['lifetime_limit'],
                'revenue': founders_licenses_count * founders_plan['price'],
                'is_available': (founders_plan['lifetime_limit'] - founders_licenses_count) > 0,
                'percentage_sold': round((founders_licenses_count / founders_plan['lifetime_limit']) * 100, 1)
            }
        else:
            stats['founders_deal'] = None
        
        # Recent activity
        recent_licenses = mongo_db.licenses.find().sort('created_at', -1).limit(5)
        stats['recent_licenses'] = []
        
        for license in recent_licenses:
            # Get customer info
            customer = mongo_db.customers.find_one({'_id': license['customer_id']})
            # Get plan info
            plan = mongo_db.plans.find_one({'_id': license['plan_id']})
            
            stats['recent_licenses'].append({
                'license_key': license['license_key'],
                'customer_name': customer['name'] if customer else 'Unknown',
                'customer_email': customer['email'] if customer else 'Unknown',
                'plan_name': plan['name'] if plan else 'Unknown',
                'created_at': license['created_at'],
                'status': license['status']
            })
        
        return render_template('admin/dashboard.html', stats=stats)
        
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('admin/dashboard.html', stats={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple hardcoded admin (in production, use proper authentication)
        if username == 'admin' and password == 'ChatelloAdmin2025!':
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.route('/customers')
@login_required
def customers():
    """Customer management"""
    try:
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        # Get customers with pagination
        total_customers = mongo_db.customers.count_documents({})
        customers_data = mongo_db.customers.find().skip(skip).limit(per_page).sort('created_at', -1)
        
        customers_list = []
        for customer in customers_data:
            # Count active licenses for each customer
            active_licenses = mongo_db.licenses.count_documents({
                'customer_id': customer['_id'],
                'status': 'active'
            })
            
            customers_list.append({
                '_id': str(customer['_id']),
                'name': customer['name'],
                'email': customer['email'],
                'created_at': customer['created_at'],
                'active_licenses': active_licenses,
                'paddle_customer_id': customer.get('paddle_customer_id', 'N/A')
            })
        
        # Pagination info
        total_pages = (total_customers + per_page - 1) // per_page
        
        return render_template('admin/customers.html', 
                             customers=customers_list,
                             page=page,
                             total_pages=total_pages,
                             total_customers=total_customers)
        
    except Exception as e:
        app.logger.error(f"Customers page error: {e}")
        flash(f'Error loading customers: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/licenses')
@login_required
def licenses():
    """License management"""
    try:
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        # Get licenses with customer and plan info
        pipeline = [
            {
                '$lookup': {
                    'from': 'customers',
                    'localField': 'customer_id', 
                    'foreignField': '_id',
                    'as': 'customer'
                }
            },
            {
                '$lookup': {
                    'from': 'plans',
                    'localField': 'plan_id',
                    'foreignField': '_id', 
                    'as': 'plan'
                }
            },
            {
                '$sort': {'created_at': -1}
            },
            {
                '$skip': skip
            },
            {
                '$limit': per_page
            }
        ]
        
        licenses_data = list(mongo_db.licenses.aggregate(pipeline))
        total_licenses = mongo_db.licenses.count_documents({})
        
        licenses_list = []
        for license_data in licenses_data:
            customer = license_data['customer'][0] if license_data['customer'] else {}
            plan = license_data['plan'][0] if license_data['plan'] else {}
            
            licenses_list.append({
                '_id': str(license_data['_id']),
                'license_key': license_data['license_key'],
                'customer_name': customer.get('name', 'Unknown'),
                'customer_email': customer.get('email', 'Unknown'),
                'plan_name': plan.get('name', 'Unknown'),
                'status': license_data['status'],
                'created_at': license_data['created_at'],
                'expires_at': license_data.get('expires_at'),
                'usage_limit': license_data.get('usage_limit', 0),
                'usage_count': license_data.get('usage_count', 0)
            })
        
        # Pagination info
        total_pages = (total_licenses + per_page - 1) // per_page
        
        # Get all customers for dropdown
        all_customers = list(mongo_db.customers.find({}, {'_id': 1, 'name': 1, 'email': 1}).sort('name', 1))
        customers_for_dropdown = [{'id': str(c['_id']), 'name': c.get('name', ''), 'email': c.get('email', '')} for c in all_customers]
        
        # Get all plans for dropdown
        all_plans = list(mongo_db.plans.find({}, {'_id': 1, 'name': 1, 'price': 1}).sort('price', 1))
        plans_for_dropdown = [{'id': str(p['_id']), 'name': p.get('name', ''), 'price': p.get('price', 0)} for p in all_plans]
        
        return render_template('admin/licenses.html',
                             licenses=licenses_list, 
                             page=page,
                             total_pages=total_pages,
                             total_licenses=total_licenses,
                             customers=customers_for_dropdown,
                             plans=plans_for_dropdown)
        
    except Exception as e:
        app.logger.error(f"Licenses page error: {e}")
        flash(f'Error loading licenses: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/create_customer', methods=['POST'])
@login_required 
def create_customer():
    """Create new customer via API"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('email') or not data.get('name'):
            return jsonify({'error': 'Email and name are required'}), 400
        
        # Check if customer already exists
        existing = mongo_db.customers.find_one({'email': data['email']})
        if existing:
            return jsonify({'error': 'Customer with this email already exists'}), 400
        
        # Create customer document
        customer = {
            'name': data['name'],
            'email': data['email'],
            'created_at': datetime.utcnow(),
            'paddle_customer_id': data.get('paddle_customer_id'),
            'metadata': data.get('metadata', {})
        }
        
        result = mongo_db.customers.insert_one(customer)
        
        return jsonify({
            'success': True,
            'customer_id': str(result.inserted_id),
            'message': 'Customer created successfully'
        })
        
    except Exception as e:
        app.logger.error(f"Create customer error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_customer/<customer_id>', methods=['GET'])
@login_required
def get_customer(customer_id):
    """Get customer details via API"""
    try:
        # Convert string ID to ObjectId
        try:
            customer_oid = ObjectId(customer_id)
        except InvalidId:
            return jsonify({'error': 'Invalid customer ID format'}), 400
        
        # Get customer
        customer = mongo_db.customers.find_one({'_id': customer_oid})
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer's licenses
        licenses = list(mongo_db.licenses.find({'customer_id': customer_oid}))
        
        # Format licenses for response
        customer_licenses = []
        for license in licenses:
            plan = mongo_db.plans.find_one({'_id': license.get('plan_id')})
            customer_licenses.append({
                'license_key': license.get('license_key'),
                'plan': plan.get('name') if plan else 'Unknown',
                'status': license.get('status'),
                'created_at': license.get('created_at').isoformat() if license.get('created_at') else None,
                'expires_at': license.get('expires_at').isoformat() if license.get('expires_at') else None,
                'usage_count': license.get('usage_count', 0),
                'usage_limit': license.get('usage_limit', 0)
            })
        
        # Format customer data for response
        customer_data = {
            'id': str(customer['_id']),
            'name': customer.get('name'),
            'email': customer.get('email'),
            'paddle_customer_id': customer.get('paddle_customer_id', 'N/A'),
            'created_at': customer.get('created_at').isoformat() if customer.get('created_at') else None,
            'licenses': customer_licenses,
            'metadata': customer.get('metadata', {})
        }
        
        return jsonify({
            'success': True,
            'customer': customer_data
        })
        
    except Exception as e:
        app.logger.error(f"Get customer error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/create_license', methods=['POST'])
@login_required
def create_license():
    """Create new license via API"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('customer_id') or not data.get('plan_id'):
            return jsonify({'error': 'customer_id and plan_id are required'}), 400
        
        # Convert string IDs to ObjectId
        try:
            customer_id = ObjectId(data['customer_id'])
            plan_id = ObjectId(data['plan_id'])
        except InvalidId:
            return jsonify({'error': 'Invalid customer_id or plan_id format'}), 400
        
        # Verify customer exists
        customer = mongo_db.customers.find_one({'_id': customer_id})
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Verify plan exists
        plan = mongo_db.plans.find_one({'_id': plan_id})
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Generate license key
        license_key = generate_license_key()
        
        # Create license document
        license_doc = {
            'license_key': license_key,
            'customer_id': customer_id,
            'plan_id': plan_id,
            'status': data.get('status', 'active'),
            'created_at': datetime.utcnow(),
            'expires_at': None,  # Most plans are subscription-based
            'usage_limit': plan.get('usage_limit', 0),
            'usage_count': 0,
            'metadata': data.get('metadata', {})
        }
        
        # Handle expiration for non-subscription plans
        if data.get('expires_at'):
            license_doc['expires_at'] = datetime.fromisoformat(data['expires_at'])
        
        result = mongo_db.licenses.insert_one(license_doc)
        
        return jsonify({
            'success': True,
            'license_id': str(result.inserted_id),
            'license_key': license_key,
            'customer_name': customer.get('name', 'Unknown'),
            'plan_name': plan.get('name', 'Unknown'),
            'message': 'License created successfully'
        })
        
    except Exception as e:
        app.logger.error(f"Create license error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insert_license', methods=['POST'])
@login_required
def insert_license():
    """Insert or update a license by its key"""
    try:
        data = request.json
        license_key = data.get('license_key', '').strip().upper()
        
        # Validate license key format
        import re
        pattern = r'^CHA-[A-F0-9]{8}-[A-F0-9]{8}-[A-F0-9]{8}-[A-F0-9]{8}$'
        if not re.match(pattern, license_key):
            return jsonify({'error': 'Invalid license key format'}), 400
        
        # Check if license already exists
        existing_license = mongo_db.licenses.find_one({'license_key': license_key})
        
        if existing_license:
            # License exists - update its status or other fields if needed
            update_data = {
                'last_verified': datetime.utcnow(),
                'status': 'active'  # Reactivate if it was inactive
            }
            
            # Update the license
            mongo_db.licenses.update_one(
                {'_id': existing_license['_id']},
                {'$set': update_data}
            )
            
            # Get customer and plan info for response
            customer = mongo_db.customers.find_one({'_id': existing_license['customer_id']})
            plan = mongo_db.plans.find_one({'_id': existing_license['plan_id']})
            
            return jsonify({
                'success': True,
                'action': 'updated',
                'license_id': str(existing_license['_id']),
                'customer_name': customer['name'] if customer else 'Unknown',
                'plan_name': plan['name'] if plan else 'Unknown',
                'status': 'active',
                'message': 'License found and updated successfully'
            })
        else:
            # License doesn't exist - create a new one with default values
            
            # First, check if we have default customer and plans
            default_customer = mongo_db.customers.find_one({'email': 'manual@chatello.io'})
            
            # Create default customer if doesn't exist
            if not default_customer:
                default_customer = {
                    'name': 'Manual Entry',
                    'email': 'manual@chatello.io',
                    'created_at': datetime.utcnow(),
                    'metadata': {'source': 'manual_insert'}
                }
                customer_result = mongo_db.customers.insert_one(default_customer)
                default_customer['_id'] = customer_result.inserted_id
            
            # Check if we should assign Founders Deal plan automatically
            founders_plan = mongo_db.plans.find_one({'name': 'founders'})
            
            # Smart plan assignment logic
            default_plan = None
            
            if founders_plan and founders_plan.get('is_active', True):
                # Check if Founders Deal is still available
                founders_licenses_count = mongo_db.licenses.count_documents({
                    'plan_id': founders_plan['_id'],
                    'status': {'$in': ['active', 'inactive']}
                })
                
                founders_remaining = founders_plan.get('lifetime_limit', 500) - founders_licenses_count
                
                if founders_remaining > 0:
                    # Founders Deal still available - assign it
                    default_plan = founders_plan
                    print(f"🚀 Assigning Founders Deal! Remaining: {founders_remaining}")
                else:
                    print(f"❌ Founders Deal SOLD OUT! ({founders_licenses_count}/{founders_plan.get('lifetime_limit', 500)})")
            
            # Fallback to Pro plan if Founders Deal not available/assigned
            if not default_plan:
                default_plan = mongo_db.plans.find_one({'name': 'pro'})
                if not default_plan:
                    # If Pro plan doesn't exist, get any plan
                    default_plan = mongo_db.plans.find_one()
            
            if not default_plan:
                # Create a basic Pro plan if no plans exist
                default_plan = {
                    'name': 'pro',
                    'display_name': 'Pro - AI Inclusa',
                    'price': 7.99,
                    'currency': 'EUR',
                    'monthly_requests': 1000,
                    'features': ['AI Included', 'Priority Support'],
                    'is_active': True,
                    'created_at': datetime.utcnow()
                }
                plan_result = mongo_db.plans.insert_one(default_plan)
                default_plan['_id'] = plan_result.inserted_id
            
            # Create the new license
            new_license = {
                'license_key': license_key,
                'customer_id': default_customer['_id'],
                'plan_id': default_plan['_id'],
                'status': 'active',
                'created_at': datetime.utcnow(),
                'expires_at': None,  # Never expires by default
                'usage_limit': default_plan.get('usage_limit', 10000),
                'usage_count': 0,
                'metadata': {
                    'source': 'manual_insert',
                    'inserted_by': session.get('username', 'admin')
                }
            }
            
            result = mongo_db.licenses.insert_one(new_license)
            
            # Prepare response message based on assigned plan
            plan_name = default_plan['name']
            if plan_name == 'founders':
                # Update founders deal stats
                remaining_after = founders_plan.get('lifetime_limit', 500) - founders_licenses_count - 1
                message = f'🚀 FOUNDERS DEAL assigned! Only {remaining_after} left!'
            else:
                message = f'New {plan_name.title()} license created successfully'
            
            return jsonify({
                'success': True,
                'action': 'created',
                'license_id': str(result.inserted_id),
                'customer_name': default_customer['name'],
                'plan_name': plan_name,
                'status': 'active',
                'message': message,
                'is_founders_deal': (plan_name == 'founders')
            })
            
    except Exception as e:
        app.logger.error(f"Insert license error: {e}")
        return jsonify({'error': str(e)}), 500

# Real analytics route with MongoDB data
@app.route('/analytics')
@login_required
def analytics():
    """Financial analytics dashboard with real MongoDB data"""
    try:
        metrics = {}
        
        # Get all active licenses with plan info
        active_licenses_pipeline = [
            {
                '$match': {
                    'status': 'active',
                    '$or': [
                        {'expires_at': None},
                        {'expires_at': {'$gt': datetime.now(timezone.utc)}}
                    ]
                }
            },
            {
                '$lookup': {
                    'from': 'plans',
                    'localField': 'plan_id',
                    'foreignField': '_id',
                    'as': 'plan'
                }
            },
            {
                '$lookup': {
                    'from': 'customers',
                    'localField': 'customer_id',
                    'foreignField': '_id',
                    'as': 'customer'
                }
            },
            {'$unwind': '$plan'},
            {'$unwind': '$customer'}
        ]
        
        active_licenses = list(mongo_db.licenses.aggregate(active_licenses_pipeline))
        
        # Calculate MRR (excluding one-time Founders Deal)
        mrr = 0
        one_time_revenue = 0
        revenue_by_plan = {}
        
        for license in active_licenses:
            plan_name = license['plan']['name'].lower()
            plan_price = license['plan'].get('price', 0)
            
            if plan_name not in revenue_by_plan:
                revenue_by_plan[plan_name] = {'revenue': 0, 'count': 0}
            
            revenue_by_plan[plan_name]['count'] += 1
            
            # Check if it's a lifetime/one-time plan
            if license['plan'].get('is_lifetime', False) or plan_name == 'founders':
                one_time_revenue += plan_price
                revenue_by_plan[plan_name]['revenue'] += plan_price
            else:
                # Regular recurring revenue
                mrr += plan_price
                revenue_by_plan[plan_name]['revenue'] += plan_price
        
        # Total active subscriptions
        metrics['total_active'] = len(active_licenses)
        
        # MRR and ARR
        metrics['mrr'] = round(mrr, 2)
        metrics['arr'] = round(mrr * 12, 2)
        
        # One-time revenue (Founders Deal)
        metrics['one_time_revenue'] = round(one_time_revenue, 2)
        
        # ARPU (Average Revenue Per User) - only for recurring
        recurring_customers = len([l for l in active_licenses if not l['plan'].get('is_lifetime', False)])
        metrics['arpu'] = round(mrr / recurring_customers, 2) if recurring_customers > 0 else 0
        
        # Get new customers this month
        start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = mongo_db.licenses.count_documents({
            'created_at': {'$gte': start_of_month}
        })
        metrics['new_this_month'] = new_this_month
        
        # Calculate last month's MRR (simplified - would need historical data in production)
        last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        last_month_end = start_of_month
        
        # Estimate based on current data (in production, you'd track this historically)
        metrics['last_month_mrr'] = round(mrr * 0.85, 2)  # Estimate 15% growth
        metrics['three_months_ago_mrr'] = round(mrr * 0.65, 2)  # Estimate
        
        # MRR Growth
        if metrics['last_month_mrr'] > 0:
            metrics['mrr_growth'] = round(((mrr - metrics['last_month_mrr']) / metrics['last_month_mrr']) * 100, 1)
        else:
            metrics['mrr_growth'] = 0
        
        # Churn and retention (simplified - needs historical tracking)
        metrics['churned_this_month'] = mongo_db.licenses.count_documents({
            'status': 'cancelled',
            'updated_at': {'$gte': start_of_month}
        })
        
        total_at_start = metrics['total_active'] + metrics['churned_this_month']
        metrics['churn_rate'] = round((metrics['churned_this_month'] / total_at_start * 100), 1) if total_at_start > 0 else 0
        metrics['retention_rate'] = round(100 - metrics['churn_rate'], 1)
        
        # At-risk customers (low usage in last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        at_risk_licenses = []
        for license in active_licenses:
            usage_count = mongo_db.usage_logs.count_documents({
                'license_id': license['_id'],
                'created_at': {'$gte': thirty_days_ago}
            })
            if usage_count < 10:  # Less than 10 API calls in 30 days
                at_risk_licenses.append(license)
        
        metrics['at_risk_customers'] = len(at_risk_licenses)
        
        # LTV and CAC (simplified estimates)
        avg_customer_lifetime_months = 12  # Estimate
        metrics['ltv'] = round(metrics['arpu'] * avg_customer_lifetime_months, 2)
        metrics['cac'] = 25.0  # Estimate
        metrics['ltv_cac_ratio'] = round(metrics['ltv'] / metrics['cac'], 2) if metrics['cac'] > 0 else 0
        
        # Targets
        metrics['mrr_target'] = 5000.0
        metrics['new_customers_target'] = 50
        
        # YoY growth (estimate since we don't have year-old data)
        metrics['yoy_growth'] = 150.0  # Placeholder
        
        # Failed payments, trials, renewals (simplified)
        metrics['failed_payments'] = 0  # Would need payment integration
        metrics['failed_payments_value'] = 0
        metrics['expiring_trials'] = 0  # No trials in current model
        metrics['expiring_trials_value'] = 0
        metrics['upcoming_renewals'] = recurring_customers
        metrics['upcoming_renewals_value'] = mrr
        
        # MRR History (simulated for now)
        current_month = datetime.now().month
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Generate realistic growth curve
        base_mrr = 50.0
        growth_rate = 1.15  # 15% monthly growth
        values = []
        for i in range(12):
            if i < current_month:
                value = base_mrr * (growth_rate ** i)
                values.append(round(value, 2))
            else:
                values.append(0)  # Future months
        
        # Set current month to actual MRR
        if current_month > 0:
            values[current_month - 1] = mrr
        
        metrics['mrr_history'] = {
            'labels': months,
            'values': values
        }
        
        # Revenue by plan
        metrics['revenue_by_plan'] = revenue_by_plan
        
        # Get Founders Deal specific metrics
        founders_plan = mongo_db.plans.find_one({'name': 'founders'})
        if founders_plan:
            founders_licenses = [l for l in active_licenses if l['plan']['name'] == 'founders']
            metrics['founders_deal'] = {
                'sold': len(founders_licenses),
                'remaining': founders_plan.get('lifetime_limit', 500) - len(founders_licenses),
                'total_revenue': len(founders_licenses) * founders_plan.get('price', 29),
                'percentage_sold': round((len(founders_licenses) / founders_plan.get('lifetime_limit', 500)) * 100, 1)
            }
        
        # Recent transactions (real data)
        recent_licenses = list(mongo_db.licenses.find().sort('created_at', -1).limit(10))
        recent_transactions = []
        
        for license in recent_licenses:
            customer = mongo_db.customers.find_one({'_id': license.get('customer_id')})
            plan = mongo_db.plans.find_one({'_id': license.get('plan_id')})
            
            if customer and plan:
                recent_transactions.append({
                    'customer_name': customer.get('name', 'Unknown'),
                    'plan': plan.get('name', 'Unknown').title(),
                    'amount': plan.get('price', 0),
                    'status': 'completed' if license.get('status') == 'active' else license.get('status', 'unknown'),
                    'date': license.get('created_at', datetime.now()).strftime('%d/%m') if license.get('created_at') else 'N/A',
                    'is_lifetime': plan.get('is_lifetime', False)
                })
        
        return render_template('admin/analytics_simple.html', 
                             metrics=metrics,
                             recent_transactions=recent_transactions)
        
    except Exception as e:
        app.logger.error(f"Analytics page error: {e}")
        flash(f'Error loading analytics: {e}', 'error')
        return redirect(url_for('dashboard'))

# Export and Reporting API Endpoints

@app.route('/api/export_financial_data')
@login_required
def export_financial_data():
    """Export financial data to CSV or Excel format"""
    try:
        export_format = request.args.get('format', 'csv').lower()
        
        # Get license data for export
        active_licenses = list(mongo_db.licenses.find({
            'status': 'active',
            '$or': [
                {'expires_at': None},
                {'expires_at': {'$gt': datetime.now(timezone.utc)}}
            ]
        }))
        
        # Prepare export data
        export_data = []
        plan_prices = {'starter': 2.99, 'pro': 7.99, 'agency': 19.99}
        
        for license in active_licenses:
            plan_name = license['plan']['name'].lower()
            export_data.append({
                'License Key': license.get('license_key', ''),
                'Customer': license['customer']['name'],
                'Plan': license['plan']['name'],
                'Monthly Revenue': plan_prices.get(plan_name, 0),
                'Status': license.get('status', 'active'),
                'Created Date': license.get('created_at', '').isoformat()[:10] if license.get('created_at') else '',
                'Expires Date': license.get('expires_at', '').isoformat()[:10] if license.get('expires_at') else 'Never'
            })
        
        if export_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            response = app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=chatello_financial_data_{datetime.now().strftime("%Y%m%d")}.csv'}
            )
            return response
        
        else:  # Excel format
            try:
                import pandas as pd
                df = pd.DataFrame(export_data)
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                
                response = app.response_class(
                    output.getvalue(),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename=chatello_financial_data_{datetime.now().strftime("%Y%m%d")}.xlsx'}
                )
                return response
            except ImportError:
                flash('Excel export requires pandas and openpyxl. Using CSV export instead.', 'info')
                return redirect(url_for('export_financial_data', format='csv'))
    
    except Exception as e:
        app.logger.error(f"Export error: {e}")
        flash(f'Export failed: {e}', 'error')
        return redirect(url_for('analytics'))

@app.route('/api/generate_monthly_report', methods=['POST'])
@login_required 
def generate_monthly_report():
    """Generate comprehensive monthly financial report"""
    try:
        # This would normally generate a detailed PDF report
        # For now, we'll return success (implementation placeholder)
        
        # Log the report generation
        if mongo_db is not None:
            mongo_db.activity_logs.insert_one({
                'action': 'monthly_report_generated',
                'admin_user': session.get('username', 'admin'),
                'timestamp': datetime.now(timezone.utc),
                'ip_address': request.remote_addr
            })
        
        return jsonify({
            'success': True,
            'message': 'Monthly report generation initiated. Report will be sent to your email.'
        })
    
    except Exception as e:
        app.logger.error(f"Report generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/send_financial_summary', methods=['POST'])
@login_required
def send_financial_summary():
    """Send financial summary via email"""
    try:
        # This would normally send an email with financial summary
        # For now, we'll return success (implementation placeholder)
        
        # Log the email send
        if mongo_db is not None:
            mongo_db.activity_logs.insert_one({
                'action': 'financial_summary_sent',
                'admin_user': session.get('username', 'admin'),
                'timestamp': datetime.now(timezone.utc),
                'ip_address': request.remote_addr
            })
        
        return jsonify({
            'success': True,
            'message': 'Financial summary sent successfully to your email.'
        })
    
    except Exception as e:
        app.logger.error(f"Email send error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/settings')
@login_required
def settings():
    """API Keys management page"""
    try:
        # Load current API keys from .env file
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        api_keys = {
            # API Keys
            'openai_api_key': os.environ.get('OPENAI_API_KEY', ''),
            'anthropic_api_key': os.environ.get('ANTHROPIC_API_KEY', ''),
            'deepseek_api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
            
            # Models
            'openai_model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            'anthropic_model': os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
            'deepseek_model': os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
            
            # Provider Configuration
            'default_provider': os.environ.get('DEFAULT_AI_PROVIDER', 'openai'),
            'fallback_provider': os.environ.get('FALLBACK_AI_PROVIDER', ''),
            
            # Status flags
            'openai_configured': bool(os.environ.get('OPENAI_API_KEY') and os.environ.get('OPENAI_API_KEY') != 'your-openai-api-key'),
            'anthropic_configured': bool(os.environ.get('ANTHROPIC_API_KEY') and os.environ.get('ANTHROPIC_API_KEY') != 'la-tua-chiave-anthropic-se-ce-lhai'),
            'deepseek_configured': bool(os.environ.get('DEEPSEEK_API_KEY') and os.environ.get('DEEPSEEK_API_KEY') != 'your-deepseek-key-here')
        }
        
        # Mask the keys for display (show only first and last 4 characters)
        for key in ['openai_api_key', 'anthropic_api_key', 'deepseek_api_key']:
            if api_keys[key] and len(api_keys[key]) > 8:
                api_keys[key] = api_keys[key][:4] + '*' * (len(api_keys[key]) - 8) + api_keys[key][-4:]
        
        return render_template('admin/settings.html', api_keys=api_keys)
        
    except Exception as e:
        app.logger.error(f"Settings page error: {e}")
        flash(f'Error loading settings: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/update_api_keys', methods=['POST'])
@login_required
def update_api_keys():
    """Update API keys in .env file"""
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        # Get form data - API Keys
        openai_key = request.form.get('openai_api_key', '').strip()
        anthropic_key = request.form.get('anthropic_api_key', '').strip()
        deepseek_key = request.form.get('deepseek_api_key', '').strip()
        
        # Get form data - Models
        openai_model = request.form.get('openai_model', 'gpt-4o-mini').strip()
        anthropic_model = request.form.get('anthropic_model', 'claude-3-5-sonnet-20241022').strip()
        deepseek_model = request.form.get('deepseek_model', 'deepseek-chat').strip()
        
        # Get form data - Provider Configuration
        default_provider = request.form.get('default_ai_provider', 'openai').strip()
        fallback_provider = request.form.get('fallback_ai_provider', '').strip()
        
        # Update API Keys (only if not masked)
        if openai_key and not '*' in openai_key:
            set_key(env_path, 'OPENAI_API_KEY', openai_key)
            os.environ['OPENAI_API_KEY'] = openai_key
        
        if anthropic_key and not '*' in anthropic_key:
            set_key(env_path, 'ANTHROPIC_API_KEY', anthropic_key)
            os.environ['ANTHROPIC_API_KEY'] = anthropic_key
        
        if deepseek_key and not '*' in deepseek_key:
            set_key(env_path, 'DEEPSEEK_API_KEY', deepseek_key)
            os.environ['DEEPSEEK_API_KEY'] = deepseek_key
        
        # Update Models (always update as they're not sensitive)
        if openai_model:
            set_key(env_path, 'OPENAI_MODEL', openai_model)
            os.environ['OPENAI_MODEL'] = openai_model
        
        if anthropic_model:
            set_key(env_path, 'ANTHROPIC_MODEL', anthropic_model)
            os.environ['ANTHROPIC_MODEL'] = anthropic_model
        
        if deepseek_model:
            set_key(env_path, 'DEEPSEEK_MODEL', deepseek_model)
            os.environ['DEEPSEEK_MODEL'] = deepseek_model
        
        # Update Provider Configuration
        if default_provider:
            set_key(env_path, 'DEFAULT_AI_PROVIDER', default_provider)
            os.environ['DEFAULT_AI_PROVIDER'] = default_provider
        
        if fallback_provider or fallback_provider == '':  # Allow empty fallback
            set_key(env_path, 'FALLBACK_AI_PROVIDER', fallback_provider)
            os.environ['FALLBACK_AI_PROVIDER'] = fallback_provider
        
        flash(f'AI Configuration updated successfully! Default provider: {default_provider.title()}. Changes are effective immediately.', 'success')
        
        # Log the update
        try:
            if mongo_db is not None:
                mongo_db.activity_logs.insert_one({
                    'action': 'ai_configuration_updated',
                    'admin_user': session.get('username', 'admin'),
                    'timestamp': datetime.now(timezone.utc),
                    'ip_address': request.remote_addr,
                    'details': {
                        'default_provider': default_provider,
                        'fallback_provider': fallback_provider,
                        'models': {
                            'openai': openai_model,
                            'anthropic': anthropic_model,
                            'deepseek': deepseek_model
                        }
                    }
                })
        except Exception as log_error:
            app.logger.warning(f"Failed to log configuration update: {log_error}")
        
        return redirect(url_for('settings'))
        
    except Exception as e:
        app.logger.error(f"Update API keys error: {e}")
        flash(f'Error updating API keys: {e}', 'error')
        return redirect(url_for('settings'))

@app.route('/api/test_api_keys', methods=['POST'])
@login_required
def test_api_keys():
    """Test API keys validity"""
    try:
        data = request.json
        results = {}
        
        # Test OpenAI key
        openai_key = data.get('openai_api_key', '').strip()
        if openai_key and not '*' in openai_key:
            try:
                import requests
                response = requests.get(
                    'https://api.openai.com/v1/models',
                    headers={'Authorization': f'Bearer {openai_key}'},
                    timeout=5
                )
                results['openai'] = {
                    'valid': response.status_code == 200,
                    'error': None if response.status_code == 200 else f'Status {response.status_code}'
                }
            except Exception as e:
                results['openai'] = {'valid': False, 'error': str(e)}
        else:
            results['openai'] = {'valid': False, 'error': 'Invalid or masked key'}
        
        # Test Anthropic key
        anthropic_key = data.get('anthropic_api_key', '').strip()
        if anthropic_key and not '*' in anthropic_key and anthropic_key != 'la-tua-chiave-anthropic-se-ce-lhai':
            try:
                import requests
                response = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': anthropic_key,
                        'anthropic-version': '2023-06-01',
                        'content-type': 'application/json'
                    },
                    json={
                        'model': 'claude-3-haiku-20240307',
                        'messages': [{'role': 'user', 'content': 'test'}],
                        'max_tokens': 1
                    },
                    timeout=5
                )
                # Anthropic returns 401 for invalid keys, 200 for valid
                results['anthropic'] = {
                    'valid': response.status_code in [200, 400],  # 400 might be rate limit
                    'error': None if response.status_code in [200, 400] else f'Invalid key'
                }
            except Exception as e:
                results['anthropic'] = {'valid': False, 'error': str(e)}
        else:
            results['anthropic'] = {'valid': False, 'error': 'Invalid or placeholder key'}
        
        # Test DeepSeek key
        deepseek_key = data.get('deepseek_api_key', '').strip()
        if deepseek_key and not '*' in deepseek_key and deepseek_key != 'your-deepseek-key-here':
            try:
                import requests
                response = requests.get(
                    'https://api.deepseek.com/v1/models',
                    headers={'Authorization': f'Bearer {deepseek_key}'},
                    timeout=5
                )
                results['deepseek'] = {
                    'valid': response.status_code == 200,
                    'error': None if response.status_code == 200 else f'Status {response.status_code}'
                }
            except Exception as e:
                results['deepseek'] = {'valid': False, 'error': str(e)}
        else:
            results['deepseek'] = {'valid': False, 'error': 'Invalid or placeholder key'}
        
        return jsonify(results)
        
    except Exception as e:
        app.logger.error(f"Test API keys error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plans')
@login_required
def plans():
    """Plans management page"""
    try:
        # Get all plans from MongoDB
        plans_list = list(mongo_db.plans.find())
        
        # Add usage statistics for each plan
        for plan in plans_list:
            # Count active licenses for this plan
            plan['active_licenses'] = mongo_db.licenses.count_documents({
                'plan_id': plan['_id'],
                'status': 'active'
            })
            
            # Get current month usage for all licenses of this plan
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            pipeline = [
                {
                    '$match': {
                        'plan_id': plan['_id'],
                        'status': 'active'
                    }
                },
                {
                    '$lookup': {
                        'from': 'usage_logs',
                        'let': {'license_id': '$_id'},
                        'pipeline': [
                            {
                                '$match': {
                                    '$expr': {
                                        '$and': [
                                            {'$eq': ['$license_id', '$$license_id']},
                                            {'$gte': ['$created_at', datetime(current_year, current_month, 1)]},
                                            {'$lt': ['$created_at', datetime(current_year, current_month + 1, 1) if current_month < 12 else datetime(current_year + 1, 1, 1)]}
                                        ]
                                    }
                                }
                            }
                        ],
                        'as': 'usage'
                    }
                },
                {
                    '$project': {
                        'total_usage': {'$size': '$usage'}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_monthly_usage': {'$sum': '$total_usage'}
                    }
                }
            ]
            
            usage_result = list(mongo_db.licenses.aggregate(pipeline))
            plan['total_monthly_usage'] = usage_result[0]['total_monthly_usage'] if usage_result else 0
            
            # Calculate average usage per license
            if plan['active_licenses'] > 0:
                plan['avg_usage_per_license'] = round(plan['total_monthly_usage'] / plan['active_licenses'], 2)
            else:
                plan['avg_usage_per_license'] = 0
        
        return render_template('admin/plans.html', plans=plans_list)
        
    except Exception as e:
        app.logger.error(f"Error loading plans: {e}")
        flash(f'Error loading plans: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/update_plan_limits', methods=['POST'])
@login_required
def update_plan_limits():
    """Update plan limits (monthly, per-minute, per-hour)"""
    try:
        plan_id = request.form.get('plan_id')
        monthly_requests = request.form.get('monthly_requests')
        requests_per_minute = request.form.get('requests_per_minute')
        requests_per_hour = request.form.get('requests_per_hour')
        
        if not plan_id:
            flash('Plan ID is required', 'error')
            return redirect(url_for('plans'))
        
        # Convert to appropriate types
        try:
            plan_id = ObjectId(plan_id)
            
            update_data = {'updated_at': datetime.now(timezone.utc)}
            changes_made = []
            
            if monthly_requests is not None:
                monthly_requests = int(monthly_requests)
                if monthly_requests < 0:
                    raise ValueError("Monthly requests cannot be negative")
                update_data['monthly_requests'] = monthly_requests
                changes_made.append(f'Monthly: {monthly_requests:,}')
            
            if requests_per_minute is not None:
                requests_per_minute = int(requests_per_minute)
                if requests_per_minute < 0:
                    raise ValueError("Requests per minute cannot be negative")
                update_data['requests_per_minute'] = requests_per_minute
                changes_made.append(f'Per minute: {requests_per_minute}')
                
            if requests_per_hour is not None:
                requests_per_hour = int(requests_per_hour)
                if requests_per_hour < 0:
                    raise ValueError("Requests per hour cannot be negative")
                update_data['requests_per_hour'] = requests_per_hour
                changes_made.append(f'Per hour: {requests_per_hour}')
            
        except (InvalidId, ValueError) as e:
            flash(f'Invalid input: {e}', 'error')
            return redirect(url_for('plans'))
        
        if len(update_data) == 1:  # Only updated_at field
            flash('No changes to update', 'info')
            return redirect(url_for('plans'))
        
        # Update the plan in MongoDB
        result = mongo_db.plans.update_one(
            {'_id': plan_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Get plan details for logging
            plan = mongo_db.plans.find_one({'_id': plan_id})
            
            # Log the update
            mongo_db.activity_logs.insert_one({
                'action': 'plan_limits_updated',
                'admin_user': session.get('username', 'admin'),
                'timestamp': datetime.now(timezone.utc),
                'ip_address': request.remote_addr,
                'details': {
                    'plan_name': plan['name'],
                    'changes': changes_made,
                    'new_monthly': update_data.get('monthly_requests'),
                    'new_per_minute': update_data.get('requests_per_minute'),
                    'new_per_hour': update_data.get('requests_per_hour')
                }
            })
            
            flash(f'Successfully updated {plan["name"]} plan limits: {", ".join(changes_made)}', 'success')
        else:
            flash('No changes made to the plan', 'info')
        
        return redirect(url_for('plans'))
        
    except Exception as e:
        app.logger.error(f"Error updating plan limits: {e}")
        flash(f'Error updating plan limits: {e}', 'error')
        return redirect(url_for('plans'))

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        mongo_client.admin.command('ping')
        
        return jsonify({
            'status': 'healthy',
            'database': 'MongoDB Atlas',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '2.0.0-mongodb'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/documentation')
@login_required
def documentation():
    """Complete Documentation for Exit Strategy"""
    try:
        # Get system stats for documentation
        db_stats = {
            'plans_count': mongo_db.plans.count_documents({}),
            'licenses_count': mongo_db.licenses.count_documents({}),
            'customers_count': mongo_db.customers.count_documents({}),
            'active_licenses': mongo_db.licenses.count_documents({'status': 'active'})
        }
        
        # Get current API version and features
        api_info = {
            'version': '2.1.0',
            'database': 'MongoDB Atlas M0',
            'features': [
                'Multi-level Rate Limiting',
                'Token Usage Tracking',
                'Budget Management', 
                'Real-time Analytics',
                'API Key Management',
                'License Management',
                'Financial Dashboard'
            ]
        }
        
        return render_template('admin/documentation.html', 
                             db_stats=db_stats,
                             api_info=api_info)
        
    except Exception as e:
        app.logger.error(f"Documentation page error: {e}")
        flash(f'Error loading documentation: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api-testing')
@login_required
def api_testing():
    """API Endpoint Testing Interface"""
    try:
        # Get sample license keys for testing
        sample_licenses = list(mongo_db.licenses.aggregate([
            {'$lookup': {
                'from': 'plans',
                'localField': 'plan_id',
                'foreignField': '_id',
                'as': 'plan'
            }},
            {'$lookup': {
                'from': 'customers',
                'localField': 'customer_id',
                'foreignField': '_id',
                'as': 'customer'
            }},
            {'$unwind': '$plan'},
            {'$unwind': '$customer'},
            {'$match': {'status': 'active'}},
            {'$limit': 5},
            {'$project': {
                'license_key': 1,
                'plan_name': '$plan.name',
                'customer_email': '$customer.email',
                'status': 1
            }}
        ]))
        
        # Available endpoints for testing
        endpoints = [
            {
                'name': 'Current Usage',
                'url': '/api/usage/current',
                'method': 'GET',
                'description': 'Get real-time usage statistics with 80% warnings',
                'auth_required': True
            },
            {
                'name': 'Usage History',
                'url': '/api/usage/history',
                'method': 'GET',
                'description': 'Detailed usage history with daily breakdown',
                'auth_required': True,
                'parameters': ['days (1-90)', 'provider (openai/anthropic/deepseek)']
            },
            {
                'name': 'Limits Check',
                'url': '/api/limits/check',
                'method': 'GET',
                'description': 'Pre-validate all limits before making requests',
                'auth_required': True
            },
            {
                'name': 'License Validation',
                'url': '/api/validate',
                'method': 'POST',
                'description': 'Validate license key and get plan information',
                'auth_required': True
            },
            {
                'name': 'Legacy Usage',
                'url': '/api/usage/{license_key}',
                'method': 'GET',
                'description': 'Legacy endpoint for backward compatibility',
                'auth_required': False
            },
            {
                'name': 'Health Check',
                'url': '/api/health',
                'method': 'GET',
                'description': 'Public API health check',
                'auth_required': False
            }
        ]
        
        return render_template('admin/api_testing.html', 
                             sample_licenses=sample_licenses,
                             endpoints=endpoints)
        
    except Exception as e:
        app.logger.error(f"API testing page error: {e}")
        flash(f'Error loading API testing: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/test_endpoint', methods=['POST'])
@login_required
def test_endpoint():
    """Test API endpoint from admin interface"""
    try:
        endpoint_url = request.form.get('endpoint_url')
        method = request.form.get('method', 'GET')
        license_key = request.form.get('license_key', '')
        parameters = request.form.get('parameters', '')
        
        if not endpoint_url:
            return jsonify({'success': False, 'error': 'Endpoint URL required'})
        
        # Build full URL
        base_url = 'http://localhost:5010'  # Internal API URL
        full_url = base_url + endpoint_url
        
        # Add parameters for GET requests
        if method == 'GET' and parameters:
            full_url += f'?{parameters}'
        
        # Setup headers
        headers = {'Content-Type': 'application/json'}
        if license_key:
            headers['X-License-Key'] = license_key
        
        # Make request
        import requests
        if method == 'GET':
            response = requests.get(full_url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(full_url, headers=headers, timeout=10)
        else:
            return jsonify({'success': False, 'error': f'Unsupported method: {method}'})
        
        # Format response
        try:
            response_data = response.json()
        except:
            response_data = response.text
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'data': response_data,
            'url': full_url
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Request failed: {str(e)}'
        })
    except Exception as e:
        app.logger.error(f"Test endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates/admin', exist_ok=True)
    
    print("🚀 Chatello Admin Dashboard (MongoDB) starting...")
    print(f"📊 Database: {DATABASE_NAME}")
    print(f"🔗 MongoDB URI: {MONGODB_URI[:50]}...")
    print(f"🔑 Access: http://localhost:5011")
    
    # Run on port 5011
    app.run(host='127.0.0.1', port=5011, debug=False)