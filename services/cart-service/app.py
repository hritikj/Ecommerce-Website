"""
Cart Service
Owns the `cart_db` database and `cart_items` table.
Enriches cart items with live product data from the Product Service.
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
DB_NAME = os.environ.get("DB_NAME", "cart_db")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://localhost:4002")


def get_db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
        if not token:
            return jsonify(error="Authentication required"), 401
        try:
            g.user = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired token"), 401
        return f(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    return jsonify(status="cart-service ok")


@app.get("/api/cart")
@require_auth
def get_cart():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cart_items WHERE user_id = %s", (g.user["id"],))
            rows = cur.fetchall()
    finally:
        conn.close()

    items = []
    for row in rows:
        try:
            resp = requests.get(f"{PRODUCT_SERVICE_URL}/api/products/{row['product_id']}", timeout=5)
            if resp.ok:
                row["product"] = resp.json()
                items.append(row)
        except requests.RequestException:
            continue
    return jsonify(items)


@app.post("/api/cart")
@require_auth
def add_to_cart():
    data = request.get_json(force=True)
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if not product_id:
        return jsonify(error="product_id is required"), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)""",
                (g.user["id"], product_id, quantity),
            )
        return jsonify(message="Item added to cart"), 201
    finally:
        conn.close()


@app.put("/api/cart/<int:product_id>")
@require_auth
def update_cart_item(product_id):
    data = request.get_json(force=True)
    quantity = data.get("quantity", 1)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if quantity <= 0:
                cur.execute("DELETE FROM cart_items WHERE user_id = %s AND product_id = %s",
                            (g.user["id"], product_id))
                return jsonify(message="Item removed")
            cur.execute("UPDATE cart_items SET quantity = %s WHERE user_id = %s AND product_id = %s",
                        (quantity, g.user["id"], product_id))
        return jsonify(message="Cart updated")
    finally:
        conn.close()


@app.delete("/api/cart/<int:product_id>")
@require_auth
def remove_cart_item(product_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cart_items WHERE user_id = %s AND product_id = %s",
                        (g.user["id"], product_id))
        return jsonify(message="Item removed")
    finally:
        conn.close()


@app.delete("/api/cart")
@require_auth
def clear_cart():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cart_items WHERE user_id = %s", (g.user["id"],))
        return jsonify(message="Cart cleared")
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4003)))
