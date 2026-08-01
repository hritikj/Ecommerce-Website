"""
Frontend Service
Server-rendered storefront (Flask + Jinja2 + Bootstrap 5). This is the
only service the browser talks to; it calls every backend microservice
through the API Gateway and keeps the JWT in the Flask session cookie.
"""
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-frontend-secret")

# Trust the X-Forwarded-* headers set by the nginx reverse proxy in front of
# this service (see nginx/default.conf) so Flask sees the real client scheme
# and host instead of the internal Docker network's.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:4000")


def auth_headers():
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def current_user():
    return session.get("user")


@app.context_processor
def inject_globals():
    cart_count = 0
    if session.get("token"):
        try:
            resp = requests.get(f"{API_BASE_URL}/api/cart", headers=auth_headers(), timeout=5)
            if resp.ok:
                cart_count = sum(i["quantity"] for i in resp.json())
        except requests.RequestException:
            pass
    return dict(current_user=current_user(), cart_count=cart_count)


@app.get("/")
def home():
    try:
        resp = requests.get(f"{API_BASE_URL}/api/products", timeout=5)
        products = resp.json()[:4] if resp.ok else []
    except requests.RequestException:
        products = []
    return render_template("home.html", products=products)


@app.get("/products")
def products():
    params = {}
    search = request.args.get("search", "")
    category_id = request.args.get("category_id", "")
    if search:
        params["search"] = search
    if category_id:
        params["category_id"] = category_id

    try:
        product_resp = requests.get(f"{API_BASE_URL}/api/products", params=params, timeout=5)
        product_list = product_resp.json() if product_resp.ok else []
        category_resp = requests.get(f"{API_BASE_URL}/api/categories", timeout=5)
        categories = category_resp.json() if category_resp.ok else []
    except requests.RequestException:
        product_list, categories = [], []

    return render_template(
        "products.html", products=product_list, categories=categories,
        search=search, category_id=category_id,
    )


@app.get("/products/<int:product_id>")
def product_detail(product_id):
    resp = requests.get(f"{API_BASE_URL}/api/products/{product_id}", timeout=5)
    if not resp.ok:
        flash("That product could not be found.", "warning")
        return redirect(url_for("products"))
    return render_template("product_detail.html", product=resp.json())


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    if not current_user():
        return redirect(url_for("login", next=request.referrer))
    quantity = int(request.form.get("quantity", 1))
    requests.post(
        f"{API_BASE_URL}/api/cart", json={"product_id": product_id, "quantity": quantity},
        headers=auth_headers(), timeout=5,
    )
    flash("Added to your cart.", "success")
    return redirect(request.referrer or url_for("products"))


@app.get("/cart")
def cart():
    if not current_user():
        return redirect(url_for("login", next=url_for("cart")))
    resp = requests.get(f"{API_BASE_URL}/api/cart", headers=auth_headers(), timeout=5)
    items = resp.json() if resp.ok else []
    subtotal = sum(float(i["product"]["price"]) * i["quantity"] for i in items)
    return render_template("cart.html", items=items, subtotal=subtotal)


@app.post("/cart/update/<int:product_id>")
def update_cart(product_id):
    quantity = int(request.form.get("quantity", 1))
    requests.put(f"{API_BASE_URL}/api/cart/{product_id}", json={"quantity": quantity},
                 headers=auth_headers(), timeout=5)
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    requests.delete(f"{API_BASE_URL}/api/cart/{product_id}", headers=auth_headers(), timeout=5)
    return redirect(url_for("cart"))


@app.get("/checkout")
def checkout():
    if not current_user():
        return redirect(url_for("login", next=url_for("checkout")))
    resp = requests.get(f"{API_BASE_URL}/api/cart", headers=auth_headers(), timeout=5)
    items = resp.json() if resp.ok else []
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("products"))
    subtotal = sum(float(i["product"]["price"]) * i["quantity"] for i in items)
    return render_template("checkout.html", items=items, subtotal=subtotal)


@app.post("/checkout")
def place_order():
    shipping_address = request.form.get("shipping_address", "")
    resp = requests.post(
        f"{API_BASE_URL}/api/orders", json={"shipping_address": shipping_address},
        headers=auth_headers(), timeout=10,
    )
    if not resp.ok:
        flash(resp.json().get("error", "We could not place your order."), "danger")
        return redirect(url_for("cart"))
    order = resp.json()
    flash(f"Order #{order['id']} placed — thank you!", "success")
    return redirect(url_for("orders"))


@app.get("/orders")
def orders():
    if not current_user():
        return redirect(url_for("login", next=url_for("orders")))
    resp = requests.get(f"{API_BASE_URL}/api/orders", headers=auth_headers(), timeout=5)
    order_list = resp.json() if resp.ok else []
    return render_template("orders.html", orders=order_list)


@app.get("/login")
def login():
    return render_template("login.html", next=request.args.get("next", ""))


@app.post("/login")
def do_login():
    email = request.form.get("email")
    password = request.form.get("password")
    resp = requests.post(f"{API_BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=5)
    if not resp.ok:
        flash(resp.json().get("error", "Login failed"), "danger")
        return redirect(url_for("login"))
    data = resp.json()
    session["token"] = data["token"]
    session["user"] = data["user"]
    flash(f"Welcome back, {data['user']['name'].split(' ')[0]}.", "success")
    return redirect(request.form.get("next") or url_for("home"))


@app.get("/register")
def register():
    return render_template("register.html")


@app.post("/register")
def do_register():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    resp = requests.post(
        f"{API_BASE_URL}/api/auth/register", json={"name": name, "email": email, "password": password}, timeout=5
    )
    if not resp.ok:
        flash(resp.json().get("error", "Registration failed"), "danger")
        return redirect(url_for("register"))
    data = resp.json()
    session["token"] = data["token"]
    session["user"] = data["user"]
    flash(f"Welcome to Fieldstead, {data['user']['name'].split(' ')[0]}!", "success")
    return redirect(url_for("home"))


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
