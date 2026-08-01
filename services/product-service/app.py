"""
Product Service
Owns the `product_db` database: `products` and `categories` tables.
Public read endpoints for browsing; admin-only writes; an internal
stock-reservation endpoint used by the Order Service during checkout.
"""
import os
import jwt
import pymysql
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "product_db")


def get_db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )


def serialize_product(row):
    # MySQL DECIMAL columns come back from PyMySQL as decimal.Decimal, which
    # Flask's JSON encoder silently turns into a *string*. Cast to float here
    # so every consumer (frontend templates, cart/order services) gets a
    # real JSON number instead of "38.00".
    if row and row.get("price") is not None:
        row["price"] = float(row["price"])
    return row


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
        if not token:
            return jsonify(error="Authentication required"), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired token"), 401
        if payload.get("role") != "admin":
            return jsonify(error="Admin access required"), 403
        return f(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    return jsonify(status="product-service ok")


@app.get("/api/products")
def list_products():
    search = request.args.get("search")
    category_id = request.args.get("category_id")
    query = """SELECT p.*, c.name AS category_name FROM products p
               LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"""
    params = []
    if search:
        query += " AND (p.name LIKE %s OR p.description LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    query += " ORDER BY p.created_at DESC"

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return jsonify([serialize_product(r) for r in rows])
    finally:
        conn.close()


@app.get("/api/products/<int:product_id>")
def get_product(product_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT p.*, c.name AS category_name FROM products p
                   LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = %s""",
                (product_id,),
            )
            product = cur.fetchone()
        if not product:
            return jsonify(error="Product not found"), 404
        return jsonify(serialize_product(product))
    finally:
        conn.close()


@app.get("/api/categories")
def list_categories():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categories ORDER BY name")
            return jsonify(cur.fetchall())
    finally:
        conn.close()


@app.post("/api/products")
@require_admin
def create_product():
    data = request.get_json(force=True)
    if not data.get("name") or data.get("price") is None:
        return jsonify(error="name and price are required"), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO products (name, description, price, stock, image_url, category_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (data["name"], data.get("description"), data["price"],
                 data.get("stock", 0), data.get("image_url"), data.get("category_id")),
            )
            return jsonify(id=cur.lastrowid), 201
    finally:
        conn.close()


@app.put("/api/products/<int:product_id>")
@require_admin
def update_product(product_id):
    data = request.get_json(force=True)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE products SET name=%s, description=%s, price=%s, stock=%s,
                   image_url=%s, category_id=%s WHERE id=%s""",
                (data.get("name"), data.get("description"), data.get("price"),
                 data.get("stock"), data.get("image_url"), data.get("category_id"), product_id),
            )
        return jsonify(message="Product updated")
    finally:
        conn.close()


@app.delete("/api/products/<int:product_id>")
@require_admin
def delete_product(product_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        return jsonify(message="Product deleted")
    finally:
        conn.close()


@app.post("/api/products/<int:product_id>/reserve-stock")
def reserve_stock(product_id):
    data = request.get_json(force=True)
    quantity = data.get("quantity", 0)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            affected = cur.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                (quantity, product_id, quantity),
            )
        if affected == 0:
            return jsonify(error="Insufficient stock"), 409
        return jsonify(message="Stock reserved")
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4002)))
