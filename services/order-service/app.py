"""
Order Service
Owns the `order_db` database: `orders` and `order_items`.
Orchestrates checkout: reads the cart from the Cart Service, reserves
stock on the Product Service, writes the order, then clears the cart.
Checking Pipeline
"""
import os
import jwt
import pymysql
import requests
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "order_db")
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://localhost:4003")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://localhost:4002")


def get_db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor, autocommit=False,
    )


def serialize_order(order):
    # MySQL DECIMAL columns come back as decimal.Decimal, which Flask's JSON
    # encoder silently stringifies. Cast to float so the frontend's
    # '%.2f'|format(...) template filter gets real numbers.
    if order.get("total") is not None:
        order["total"] = float(order["total"])
    for item in order.get("items", []):
        if item.get("unit_price") is not None:
            item["unit_price"] = float(item["unit_price"])
    return order


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
        if not token:
            return jsonify(error="Authentication required"), 401
        try:
            g.user = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            g.auth_header = auth_header
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired token"), 401
        return f(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    return jsonify(status="order-service ok")


@app.post("/api/orders")
@require_auth
def place_order():
    shipping_address = (request.get_json(silent=True) or {}).get("shipping_address")

    # 1. Fetch the current cart (already enriched with product data)
    cart_resp = requests.get(f"{CART_SERVICE_URL}/api/cart", headers={"Authorization": g.auth_header}, timeout=5)
    cart_items = cart_resp.json() if cart_resp.ok else []
    if not cart_items:
        return jsonify(error="Cart is empty"), 400

    # 2. Reserve stock for every item; bail out if anything is unavailable
    for item in cart_items:
        resp = requests.post(
            f"{PRODUCT_SERVICE_URL}/api/products/{item['product_id']}/reserve-stock",
            json={"quantity": item["quantity"]}, timeout=5,
        )
        if not resp.ok:
            return jsonify(error=f"'{item['product']['name']}' no longer has enough stock"), 409

    total = sum(float(item["product"]["price"]) * item["quantity"] for item in cart_items)

    # 3. Persist the order + line items in a single transaction
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_id, total, status, shipping_address) VALUES (%s, %s, %s, %s)",
                (g.user["id"], total, "paid", shipping_address),
            )
            order_id = cur.lastrowid
            for item in cart_items:
                cur.execute(
                    """INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (order_id, item["product_id"], item["product"]["name"], item["product"]["price"], item["quantity"]),
                )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        return jsonify(error="Failed to place order"), 500
    finally:
        conn.close()

    # 4. Clear the cart now that the order is placed
    requests.delete(f"{CART_SERVICE_URL}/api/cart", headers={"Authorization": g.auth_header}, timeout=5)

    return jsonify(id=order_id, total=total, status="paid"), 201


@app.get("/api/orders")
@require_auth
def list_orders():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC", (g.user["id"],))
            orders = cur.fetchall()
            for order in orders:
                cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order["id"],))
                order["items"] = cur.fetchall()
        return jsonify([serialize_order(o) for o in orders])
    finally:
        conn.close()


@app.get("/api/orders/<int:order_id>")
@require_auth
def get_order(order_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s AND user_id = %s", (order_id, g.user["id"]))
            order = cur.fetchone()
            if not order:
                return jsonify(error="Order not found"), 404
            cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            order["items"] = cur.fetchall()
        return jsonify(serialize_order(order))
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4004)))
