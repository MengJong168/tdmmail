from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
import time
import requests
import json

app = Flask(__name__)
app.secret_key = 'replace_with_a_random_secret_key'  # change in production

# API configuration - point to your create_database.py server
API_BASE_URL = 'http://localhost:5003'  # Change this if your server runs on different port

# Remove all local database functions and replace with API calls

# Authentication routes - Updated to handle both JSON and form data
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
    
    if not username or not password:
        if request.is_json:
            return jsonify({"success": False, "error": "Username and password are required"}), 400
        else:
            return render_template('register.html', error='Username and password are required')
    
    try:
        # Register user via API
        response = requests.post(
            f'{API_BASE_URL}/api/users/register',
            json={'username': username, 'password': password},
            timeout=10
        )
        data = response.json()
        
        if data.get('success'):
            session['user'] = username
            session['user_id'] = data.get('user_id')
            if request.is_json:
                return jsonify({"success": True, "user_id": data.get('user_id'), "message": "User registered successfully"})
            else:
                return redirect(url_for('index'))
        else:
            error_msg = data.get('error', 'Registration failed')
            if request.is_json:
                return jsonify({"success": False, "error": error_msg}), 400
            else:
                return render_template('register.html', error=error_msg)
            
    except Exception as e:
        error_msg = f'API error: {str(e)}'
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 500
        else:
            return render_template('register.html', error=error_msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
    
    if not username or not password:
        if request.is_json:
            return jsonify({"success": False, "error": "Username and password are required"}), 400
        else:
            return render_template('login.html', error='Username and password are required')
    
    try:
        # Login user via API
        response = requests.post(
            f'{API_BASE_URL}/api/users/login',
            json={'username': username, 'password': password},
            timeout=10
        )
        data = response.json()
        
        if data.get('success'):
            user_data = data.get('user', {})
            session['user'] = user_data.get('username')
            session['user_id'] = user_data.get('id')
            if request.is_json:
                return jsonify({
                    "success": True, 
                    "user": {
                        "id": user_data.get('id'),
                        "username": user_data.get('username'),
                        "balance": user_data.get('balance')
                    }
                })
            else:
                return redirect(url_for('index'))
        else:
            error_msg = data.get('error', 'Invalid credentials')
            if request.is_json:
                return jsonify({"success": False, "error": error_msg}), 401
            else:
                return render_template('login.html', error=error_msg)
                
    except Exception as e:
        error_msg = f'API error: {str(e)}'
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 500
        else:
            return render_template('login.html', error=error_msg)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

# Orders page
@app.route('/orders')
def orders_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get user balance via API
        balance_response = requests.get(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/balance',
            timeout=10
        )
        balance_data = balance_response.json()
        balance = balance_data.get('balance', 0.0) if balance_data.get('success') else 0.0
        
        # Get orders via API
        orders_response = requests.get(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/orders',
            timeout=10
        )
        orders_data = orders_response.json()
        
        orders = orders_data.get('orders', []) if orders_data.get('success') else []
        
        # Format dates for orders
        for order in orders:
            if order.get('created_at'):
                try:
                    if isinstance(order['created_at'], str):
                        dt = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                        order['formatted_date'] = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        order['formatted_date'] = order['created_at'].strftime('%Y-%m-%d %H:%M')
                except:
                    order['formatted_date'] = 'Unknown date'
            else:
                order['formatted_date'] = 'Unknown date'
        
        return render_template('orders.html', orders=orders, balance=balance)
        
    except Exception as e:
        print(f"Error loading orders: {e}")
        return render_template('orders.html', orders=[], balance=0.0)

# Original order creation (for backward compatibility)
@app.route('/create_order', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    data = request.form
    order_id = f"ORD{int(time.time()*1000)}"
    
    try:
        # Create order via API
        response = requests.post(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/orders',
            json={
                'order_id': order_id,
                'product': data.get('product', 'Item'),
                'price': float(data.get('price', 0))
            },
            timeout=10
        )
        
        if response.json().get('success'):
            return redirect(url_for('orders_page'))
        else:
            return "Error creating order", 500
            
    except Exception as e:
        return f"API error: {str(e)}", 500

# Balance page
@app.route('/balance')
def balance_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get user balance via API
        balance_response = requests.get(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/balance',
            timeout=10
        )
        balance_data = balance_response.json()
        balance = balance_data.get('balance', 0.0) if balance_data.get('success') else 0.0
        
        # Get transactions via API
        transactions_response = requests.get(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/transactions',
            timeout=10
        )
        transactions_data = transactions_response.json()
        
        transactions = transactions_data.get('transactions', []) if transactions_data.get('success') else []
        
        # Format dates for transactions
        for tx in transactions:
            if tx.get('created_at'):
                try:
                    if isinstance(tx['created_at'], str):
                        dt = datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00'))
                        tx['formatted_date'] = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        tx['formatted_date'] = tx['created_at'].strftime('%Y-%m-%d %H:%M')
                except:
                    tx['formatted_date'] = 'Unknown date'
            else:
                tx['formatted_date'] = 'Unknown date'
        
        return render_template('balance.html', balance=balance, transactions=transactions)
        
    except Exception as e:
        print(f"Error loading balance: {e}")
        return render_template('balance.html', balance=0.0, transactions=[])

# QR Code routes
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        amount = float(request.form['amount'])
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
        if amount > 10000:
            return jsonify({'error': 'Maximum amount is $10,000'}), 400

        transaction_id = f"TRX{int(time.time())}"
        
        # Generate QR code using KHQR
        qr_data = khqr.create_qr(
            bank_account='meng_topup@aclb',
            merchant_name='MailShop',
            merchant_city='Phnom Penh',
            amount=amount,
            currency='USD',
            store_label='MShop',
            phone_number='855976666666',
            bill_number=transaction_id,
            terminal_label='Cashier-01',
            static=False
        )
        md5_hash = khqr.generate_md5(qr_data)

        qr_img = qrcode.make(qr_data)
        img_io = BytesIO()
        qr_img.save(img_io, 'PNG')
        img_io.seek(0)
        qr_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        expiry = datetime.now() + timedelta(minutes=3)
        
        # Create transaction via API
        try:
            response = requests.post(
                f'{API_BASE_URL}/api/users/{session["user_id"]}/transactions',
                json={
                    'transaction_id': transaction_id,
                    'amount': amount,
                    'md5_hash': md5_hash,
                    'expiry': expiry.isoformat()
                },
                timeout=10
            )
            
            if not response.json().get('success'):
                print("Warning: Failed to save transaction to API")
                
        except Exception as e:
            print(f"Warning: Failed to save transaction to API: {e}")

        return jsonify({
            'success': True,
            'qr_image': qr_base64,
            'transaction_id': transaction_id,
            'amount': amount,
            'expiry': expiry.isoformat()
        })
    except Exception as e:
        print(f"Error generating QR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_payment', methods=['POST', 'GET'])
def check_payment():
    try:
        if request.method == 'POST':
            if 'user_id' not in session:
                return jsonify({'error': 'Please login first'}), 401
            
            transaction_id = request.form.get('transaction_id')
            if not transaction_id:
                return jsonify({'error': 'Missing transaction_id'}), 400

            # Check transaction via API
            try:
                response = requests.get(
                    f'{API_BASE_URL}/api/users/{session["user_id"]}/transactions/{transaction_id}',
                    timeout=10
                )
                transaction_data = response.json()
                
                if not transaction_data.get('success'):
                    return jsonify({'error': 'Transaction not found'}), 404
                    
                transaction = transaction_data.get('transaction', {})
                md5_hash = transaction.get('md5_hash')
                
            except Exception as e:
                return jsonify({'error': f'API error: {str(e)}'}), 500

        else:  # GET request with md5 parameter
            md5_hash = request.args.get('md5')
            if not md5_hash:
                return jsonify({'error': 'Missing md5 parameter'}), 400

        # Check payment status via external API
        external_api = f'https://mengtopup.shop/api/check_payment?md5={md5_hash}'
        response = requests.get(external_api, timeout=10)
        if response.status_code != 200:
            return jsonify({'status': 'ERROR', 'message': 'Failed to fetch status from external API'}), 502
        
        data = response.json()
        status = data.get('status')

        # Optional: simulate paid for testing
        if request.form.get('simulate_paid') == '1' or request.args.get('simulate_paid') == '1':
            status = "PAID"
            print("Simulating paid transaction for testing")

        if status == "PAID":
            # Update transaction status via API
            try:
                update_response = requests.post(
                    f'{API_BASE_URL}/api/users/{md5_hash}/paid',
                    timeout=10
                )
                update_data = update_response.json()
                if update_data.get('success'):
                    print(f"Payment credited via API for hash: {md5_hash}")
                else:
                    print(f"Failed to credit payment: {update_data.get('error')}")
            except Exception as e:
                    print(f"Warning: Failed to update transaction status via API: {e}")
        

        return jsonify({
            'status': status,
            'message': data.get('message', ''),
        })

    except Exception as e:
        print(f"Error checking payment: {e}")
        return jsonify({'error': str(e)}), 500

# OTP Service routes (updated to use API)
@app.route('/create_api_order', methods=['POST'])
def create_api_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    service = data.get('service')
    
    if not service:
        return jsonify({'error': 'Service is required'}), 400
    
    # Check user balance via API
    try:
        balance_response = requests.get(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/balance',
            timeout=10
        )
        balance_data = balance_response.json()
        
        if not balance_data.get('success'):
            return jsonify({'error': 'Failed to check balance'}), 500
            
        user_balance = balance_data.get('balance', 0.0)
        service_cost = 0.045
        
        if user_balance < service_cost:
            return jsonify({'error': f'Insufficient balance. You need ${service_cost:.3f} but have ${user_balance:.2f}'}), 400
            
    except Exception as e:
        return jsonify({'error': f'API error: {str(e)}'}), 500
    
    try:
        # Call external API to create order
        api_url = f"https://yshshopmails.shop/v1/api/create-order.php?key=Ua7CfOBAGanCwzIMBxQt3YEjMBt8F11L&service={service}"
        response = requests.get(api_url, timeout=30)
        api_data = response.json()
        
        if 'mail' in api_data and 'order_id' in api_data:
            # Save order to API
            order_response = requests.post(
                f'{API_BASE_URL}/api/users/{session["user_id"]}/orders',
                json={
                    'order_id': api_data['order_id'],
                    'mail': api_data['mail'],
                    'service': service,
                    'status': 'running'
                },
                timeout=10
            )
            
            if order_response.json().get('success'):
                return jsonify({
                    'success': True,
                    'mail': api_data['mail'],
                    'order_id': api_data['order_id'],
                    'cost': '0.045'
                })
            else:
                return jsonify({'error': 'Failed to save order to database'}), 500
        else:
            return jsonify({'error': api_data.get('error', 'Failed to create order')}), 400
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'API request timeout'}), 408
    except Exception as e:
        print(f"Error creating API order: {e}")
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/check_api_otp', methods=['POST'])
def check_api_otp():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    order_id = data.get('order_id')
    service = data.get('service')
    
    if not order_id:
        return jsonify({'error': 'Order ID is required'}), 400
    
    try:
        # Call external API to check OTP
        api_url = f"https://yshshopmails.shop/v1/api/check-otp.php?key=Ua7CfOBAGanCwzIMBxQt3YEjMBt8F11L&id={order_id}"
        response = requests.get(api_url, timeout=30)
        api_data = response.json()
        
        if 'otp' in api_data and api_data['otp']:
            # OTP received - process via API
            amount = float(api_data.get('amount', 0.045))
            
            # Update order with OTP via API
            update_response = requests.post(
                f'{API_BASE_URL}/api/users/{session["user_id"]}/orders/{order_id}/otp',
                json={
                    'otp': api_data['otp'],
                    'amount': amount
                },
                timeout=10
            )
            
            update_data = update_response.json()
            
            if update_data.get('success'):
                return jsonify({
                    'success': True,
                    'otp': api_data['otp'],
                    'amount': amount,
                    'message': 'OTP received successfully'
                })
            else:
                return jsonify({'error': update_data.get('error', 'Failed to process OTP')}), 500
        else:
            return jsonify({'error': 'No OTP received yet'})
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'API request timeout'}), 408
    except Exception as e:
        print(f"Error checking API OTP: {e}")
        return jsonify({'error': 'Failed to check OTP'}), 500

@app.route('/complete_order', methods=['POST'])
def complete_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    order_id = data.get('order_id')
    
    if not order_id:
        return jsonify({'error': 'Order ID is required'}), 400
    
    try:
        # Mark order as completed via API
        response = requests.post(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/orders/{order_id}/complete',
            timeout=10
        )
        
        if response.json().get('success'):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to complete order'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    
    if not order_id or not status:
        return jsonify({'error': 'Order ID and status are required'}), 400
    
    try:
        # Update order status via API
        response = requests.post(
            f'{API_BASE_URL}/api/users/{session["user_id"]}/orders/{order_id}/status',
            json={'status': status},
            timeout=10
        )
        
        if response.json().get('success'):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update order status'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Remove all local database debug routes and replace with API-based ones if needed

# Bakong KHQR integration (keep this as is)
try:
    from bakong_khqr import KHQR
    api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiMmEyMDE3MzUxMGU4NDZhMiJ9LCJpYXQiOjE3NTk3MjIzNjAsImV4cCI6MTc2NzQ5ODM2MH0._d3PWPYi-N_mPyt-Ntxj5qbtHghOdtZhka2LbdJlKRw"
    khqr = KHQR(api_token)
    print("Bakong KHQR initialized with real API token")
except Exception as e:
    print(f"Bakong KHQR initialization failed: {e}")
    class KHQRStub:
        def __init__(self, token):
            self.token = token
            print("Using KHQR stub implementation")
        def create_qr(self, **kwargs):
            payload = f"BKQR|{kwargs.get('bill_number')}|{kwargs.get('amount')}|{kwargs.get('currency','USD')}"
            print(f"Generated QR payload: {payload}")
            return payload
        def generate_md5(self, payload):
            import hashlib
            return hashlib.md5(payload.encode()).hexdigest()
        def check_payment(self, md5_hash):
            print(f"Checking payment for hash: {md5_hash}")
            return "UNPAID"
    khqr = KHQRStub("stub-token")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
