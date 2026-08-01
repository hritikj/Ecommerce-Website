# Fieldstead — Flask Microservice Ecommerce Demo

A simple ecommerce site built as independent Flask microservices, each with
its own MySQL database, plus a server-rendered Bootstrap 5 storefront.

## Architecture

```
                         ┌─────────────────┐
                         │   Browser        │
                         └────────┬─────────┘
                                  │  HTML / forms
                         ┌────────▼─────────┐
                         │  Frontend (Flask  │  :3000
                         │  + Jinja2 +       │  session cookie holds JWT
                         │  Bootstrap 5)     │
                         └────────┬─────────┘
                                  │  REST (JSON) + Bearer token
                         ┌────────▼─────────┐
                         │   API Gateway     │  :4000
                         │   (Flask proxy)   │
                         └───┬───┬───┬───┬───┘
              ┌──────────────┘   │   │   └──────────────┐
     ┌────────▼──────┐  ┌────────▼───┐ ┌───▼─────────┐ ┌─▼────────────┐
     │ Auth Service  │  │ Product    │ │ Cart Service │ │ Order Service│
     │   :4001       │  │ Service    │ │   :4003      │ │   :4004      │
     │               │  │  :4002     │ │ (calls       │ │ (calls Cart +│
     │               │  │            │ │  Product Svc)│ │  Product Svc)│
     └───────┬───────┘  └──────┬─────┘ └──────┬───────┘ └──────┬───────┘
             │                 │              │                │
        ┌────▼────┐       ┌────▼────┐    ┌────▼────┐      ┌────▼────┐
        │auth_db  │       │product_db│    │ cart_db │      │order_db │
        └─────────┘       └─────────┘    └─────────┘      └─────────┘
                 all four databases live in one MySQL container
```

**Database-per-service**: each service owns its own schema (`auth_db`,
`product_db`, `cart_db`, `order_db`) and never queries another service's
tables directly — cross-service data (e.g. cart needing product prices)
is fetched over HTTP.

**Auth**: the Auth Service issues a JWT on login/register. The frontend
stores it server-side in the Flask session cookie and attaches it as a
`Bearer` token on every API Gateway call. Cart and Order services verify
the same JWT independently (shared `JWT_SECRET`).

**Checkout flow**: Order Service reads the cart from Cart Service →
reserves stock on Product Service (atomic `UPDATE ... WHERE stock >= ?`)
→ writes `orders` + `order_items` in a DB transaction → clears the cart.

## Folder structure

```
ecommerce-flask-microservices/
├── docker-compose.yml
├── mysql-init/                 # schema + seed data, run once on first boot
│   ├── 01-auth.sql
│   ├── 02-products.sql
│   ├── 03-cart.sql
│   └── 04-orders.sql
├── api-gateway/                # Flask reverse proxy, :4000
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── services/
│   ├── auth-service/           # :4001 — users, JWT
│   ├── product-service/        # :4002 — products, categories, stock
│   ├── cart-service/           # :4003 — per-user cart
│   └── order-service/          # :4004 — checkout orchestration, orders
│       each with app.py, requirements.txt, Dockerfile
└── frontend/                   # :3000 — Flask + Jinja2 + Bootstrap 5
    ├── app.py
    ├── requirements.txt
    ├── Dockerfile
    ├── templates/               # base, home, products, product_detail,
    │                             # cart, checkout, orders, login, register
    └── static/css/custom.css    # Fieldstead color/type identity
```

## Running it

```bash
docker compose up --build
```

Then open **http://localhost:3000**. MySQL, all four backend services,
the gateway, and the frontend all start together; `mysql-init/*.sql`
seeds sample products the first time the `mysql` volume is created.

To reset the database from scratch: `docker compose down -v`.

## Running services individually (without Docker)

Each Python service needs its own virtualenv:

```bash
cd services/auth-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
DB_HOST=localhost DB_PASSWORD=root python app.py
```

Repeat for `product-service`, `cart-service`, `order-service`,
`api-gateway`, and `frontend`, pointing each at a running local MySQL
instance with the databases from `mysql-init/`.

## Default sample data

`mysql-init/02-products.sql` seeds 8 products across 4 categories
(Home Goods, Kitchen, Apparel, Stationery) so the storefront isn't empty
on first run. There is no seeded admin user — register a normal account
through the UI; to make it an admin (needed for the product-management
endpoints), update its role directly:

```sql
UPDATE auth_db.users SET role = 'admin' WHERE email = 'you@example.com';
```

## Notes & next steps for production

- Swap the shared `JWT_SECRET` env var for real per-environment secrets management.
- Put MySQL behind a managed instance (RDS/Cloud SQL) rather than a container, one schema per service or separate instances entirely.
- Add rate limiting and request validation (e.g. `pydantic`/`marshmallow`) at the gateway.
- Put a real reverse proxy / load balancer (nginx, Traefik) in front of the gateway and run multiple replicas of each service.
- Add a payment provider integration in Order Service instead of marking orders `paid` immediately.
