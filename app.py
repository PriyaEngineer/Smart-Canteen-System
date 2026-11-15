
from flask import Flask, render_template, request, redirect, url_for, session
from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)

app.secret_key = "smart_canteen_dev_secret_2026"


# HOME PAGE
@app.route('/')
def home():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM menu_items WHERE is_available = TRUE"
    )
    menu_items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('index.html', menu_items=menu_items)


# STUDENT REGISTRATION
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        college_id = request.form['college_id']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match!"

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO users (name, college_id, email, password)
        VALUES (%s, %s, %s, %s)
        """

        try:
            cursor.execute(
                query,
                (name, college_id, email, hashed_password)
            )
            connection.commit()

        except Exception:
            connection.rollback()
            return "College ID or Email already registered!"

        finally:
            cursor.close()
            connection.close()

        return render_template('success.html')

    return render_template('register.html')


# ADMIN LOGIN
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        identifier = request.form['identifier']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT * FROM users
        WHERE (college_id = %s OR email = %s)
        AND role = 'admin'
        LIMIT 1
        """

        cursor.execute(query, (identifier, identifier))
        admin = cursor.fetchone()

        cursor.close()
        connection.close()

        if admin and check_password_hash(admin['password'], password):

            session['admin_id'] = admin['user_id']
            session['admin_name'] = admin['name']

            return redirect(url_for('admin_dashboard'))

        return render_template(
            'admin_login.html',
            error="Invalid Admin ID/Email or Password!"
        )

    return render_template('admin_login.html')

# ADMIN DASHBOARD
@app.route('/admin/dashboard')
def admin_dashboard():

    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.order_id,
        o.order_date,
        o.total_amount,
        o.status,
        o.preparation_time,
        o.pickup_time,
        u.name AS student_name,
        u.college_id
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
    ORDER BY o.order_date DESC
    """

    cursor.execute(query)
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'admin_dashboard.html',
        orders=orders
    )

# ADMIN ORDER UPDATE
@app.route('/admin/order/update/<int:order_id>', methods=['POST'])
def update_order(order_id):

    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    action = request.form.get('action')

    connection = get_db_connection()
    cursor = connection.cursor()

    if action == 'accept':

        preparation_time = request.form.get('preparation_time')

        if preparation_time not in ['10', '15', '20', '30']:
            cursor.close()
            connection.close()
            return redirect(url_for('admin_dashboard'))

        query = """
        UPDATE orders
        SET status = 'Accepted',
            preparation_time = %s
        WHERE order_id = %s AND status = 'Pending'
        """

        cursor.execute(query, (int(preparation_time), order_id))

    elif action == 'reject':

        query = """
        UPDATE orders
        SET status = 'Rejected'
        WHERE order_id = %s AND status = 'Pending'
        """

        cursor.execute(query, (order_id,))

    elif action == 'preparing':

        query = """
        UPDATE orders
        SET status = 'Preparing'
        WHERE order_id = %s AND status = 'Accepted'
        """

        cursor.execute(query, (order_id,))

    elif action == 'ready':

        query = """
        UPDATE orders
        SET status = 'Ready for Pickup'
        WHERE order_id = %s AND status = 'Preparing'
        """

        cursor.execute(query, (order_id,))

    elif action == 'completed':

        query = """
        UPDATE orders
        SET status = 'Completed'
        WHERE order_id = %s AND status = 'Ready for Pickup'
        """

        cursor.execute(query, (order_id,))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('admin_dashboard'))

# STUDENT LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        identifier = request.form['identifier']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT * FROM users
        WHERE (college_id = %s OR email = %s)
        AND role = 'student'
        LIMIT 1
        """

        cursor.execute(query, (identifier, identifier))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(user['password'], password):

            session['user_id'] = user['user_id']
            session['student_name'] = user['name']

            return redirect(url_for('dashboard'))

        return render_template(
            'login.html',
            error="Invalid College ID/Email or Password!"
        )

    return render_template('login.html')


# STUDENT DASHBOARD
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM menu_items WHERE is_available = TRUE"
    )
    menu_items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'dashboard.html',
        student_name=session['student_name'],
        menu_items=menu_items
    )


# STUDENT MY ORDERS
@app.route('/orders')
def my_orders():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.order_id,
        o.order_date,
        o.total_amount,
        o.status,
        o.pickup_time,
        o.preparation_time,
        oi.quantity,
        oi.price,
        mi.item_name
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN menu_items mi ON oi.item_id = mi.item_id
    WHERE o.user_id = %s
    ORDER BY o.order_date DESC, o.order_id DESC
    """

    cursor.execute(query, (session['user_id'],))
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    orders = {}

    for row in rows:

        order_id = row['order_id']

        if order_id not in orders:
            orders[order_id] = {
                'order_id': order_id,
                'order_date': row['order_date'],
                'total_amount': row['total_amount'],
                'status': row['status'],
                'pickup_time': row['pickup_time'],
                'preparation_time': row['preparation_time'],
                'items': []
            }

        orders[order_id]['items'].append({
            'item_name': row['item_name'],
            'quantity': row['quantity'],
            'price': row['price']
        })

    return render_template(
        'my_orders.html',
        orders=list(orders.values())
    )

# ADD ITEM TO CARTpython app.py
@app.route('/cart/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT item_id FROM menu_items
        WHERE item_id = %s AND is_available = TRUE
        """,
        (item_id,)
    )

    item = cursor.fetchone()

    cursor.close()
    connection.close()

    if not item:
        return redirect(url_for('dashboard'))

    cart = session.get('cart', {})
    item_key = str(item_id)

    current_quantity = cart.get(item_key, 0)

    if current_quantity < 20:
        cart[item_key] = current_quantity + 1

    session['cart'] = cart

    return redirect(url_for('cart'))



# VIEW CART
@app.route('/cart')
def cart():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_data = session.get('cart', {})
    cart_items = []
    total = Decimal('0.00')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    for item_id, quantity in cart_data.items():

        cursor.execute(
            """
            SELECT * FROM menu_items
            WHERE item_id = %s AND is_available = TRUE
            """,
            (int(item_id),)
        )

        item = cursor.fetchone()

        if item:
            item['quantity'] = quantity
            item['subtotal'] = item['price'] * quantity

            total += item['subtotal']
            cart_items.append(item)

    cursor.close()
    connection.close()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total=total
    )


# UPDATE CART QUANTITY
@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        quantity = int(request.form['quantity'])
    except (ValueError, TypeError):
        return redirect(url_for('cart'))

    cart = session.get('cart', {})
    item_key = str(item_id)

    if item_key in cart:

        if 1 <= quantity <= 20:
            cart[item_key] = quantity

    session['cart'] = cart

    return redirect(url_for('cart'))


# REMOVE ITEM FROM CART
@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    cart.pop(str(item_id), None)

    session['cart'] = cart

    return redirect(url_for('cart'))


# CHECKOUT PAGE
@app.route('/checkout')
def checkout():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_data = session.get('cart', {})

    if not cart_data:
        return redirect(url_for('dashboard'))

    cart_items = []
    total = Decimal('0.00')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    for item_id, quantity in cart_data.items():

        cursor.execute(
            """
            SELECT * FROM menu_items
            WHERE item_id = %s AND is_available = TRUE
            """,
            (int(item_id),)
        )

        item = cursor.fetchone()

        if item:
            item['quantity'] = quantity
            item['subtotal'] = item['price'] * quantity
            total += item['subtotal']
            cart_items.append(item)

    cursor.close()
    connection.close()

    if not cart_items:
        return redirect(url_for('dashboard'))

    return render_template(
        'checkout.html',
        cart_items=cart_items,
        total=total
    )


# PLACE ORDER
@app.route('/place-order', methods=['POST'])
def place_order():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_data = session.get('cart', {})

    if not cart_data:
        return redirect(url_for('dashboard'))

    pickup_value = request.form.get('pickup_time', '')

    try:
        pickup_time = datetime.strptime(
            pickup_value,
            '%Y-%m-%dT%H:%M'
        )

        if pickup_time <= datetime.now():
            return "Please select a future pickup time."

    except ValueError:
        return "Please select a valid pickup time."

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        total = Decimal('0.00')
        order_items = []

        # Fetch current prices from database
        for item_id, quantity in cart_data.items():

            if not 1 <= int(quantity) <= 20:
                raise ValueError("Invalid quantity")

            cursor.execute(
                """
                SELECT * FROM menu_items
                WHERE item_id = %s AND is_available = TRUE
                """,
                (int(item_id),)
            )

            item = cursor.fetchone()

            if not item:
                raise ValueError("A selected item is unavailable.")

            subtotal = item['price'] * int(quantity)

            total += subtotal

            order_items.append(
                (int(item_id), int(quantity), item['price'])
            )

        # Save order in orders table
        cursor.execute(
            """
            INSERT INTO orders (user_id, total_amount, pickup_time)
            VALUES (%s, %s, %s)
            """,
            (session['user_id'], total, pickup_time)
        )

        order_id = cursor.lastrowid

        # Save individual items in order_items table
        for item_id, quantity, price in order_items:

            cursor.execute(
                """
                INSERT INTO order_items
                (order_id, item_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (order_id, item_id, quantity, price)
            )

        connection.commit()

        session.pop('cart', None)

        return render_template(
            'order_success.html',
            order_id=order_id,
            total=total,
            pickup_time=pickup_time
        )

    except Exception as error:

        connection.rollback()

        return render_template(
            'checkout.html',
            cart_items=[],
            total=Decimal('0.00'),
            error=str(error)
        )

    finally:
        cursor.close()
        connection.close()


# LOGOUT
@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return connection

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)