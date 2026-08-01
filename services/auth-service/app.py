"""
Auth Service
Owns the `auth_db` database and the `users` table.
Handles registration, login, and JWT issuance/verification.
"""
import os
import datetime
import jwt
import bcrypt
import pymysql
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "auth_db")


def get_db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )


def make_token(user):
    payload = {
        "id": user["id"], "name": user["name"], "email": user["email"],
        "role": user["role"], "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@app.get("/health")
def health():
    return jsonify(status="auth-service ok")


@app.post("/api/auth/register")
def register():
    data = request.get_json(force=True)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not name or not email or not password:
        return jsonify(error="name, email and password are required"), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify(error="An account with this email already exists"), 409

            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash),
            )
            user_id = cur.lastrowid

        user = {"id": user_id, "name": name, "email": email, "role": "customer"}
        return jsonify(token=make_token(user), user=user), 201
    finally:
        conn.close()


@app.post("/api/auth/login")
def login():
    data = request.get_json(force=True)
    email, password = data.get("email"), data.get("password")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return jsonify(error="Invalid email or password"), 401

        public_user = {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}
        return jsonify(token=make_token(public_user), user=public_user)
    finally:
        conn.close()


@app.get("/api/auth/me")
def me():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
    if not token:
        return jsonify(error="No token provided"), 401
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return jsonify(user=payload)
    except jwt.PyJWTError:
        return jsonify(error="Invalid or expired token"), 401


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4001)))
