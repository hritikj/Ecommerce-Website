"""
API Gateway
Single entry point for the frontend. Forwards each request to the
correct downstream microservice based on the URL prefix.
"""
import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:4001")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://localhost:4002")
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://localhost:4003")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://localhost:4004")

ROUTES = {
    "auth": AUTH_SERVICE_URL,
    "products": PRODUCT_SERVICE_URL,
    "categories": PRODUCT_SERVICE_URL,
    "cart": CART_SERVICE_URL,
    "orders": ORDER_SERVICE_URL,
}

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
              "te", "trailers", "transfer-encoding", "upgrade", "content-encoding", "content-length"}


@app.get("/health")
def health():
    return jsonify(status="gateway ok")


@app.route("/api/<segment>", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/api/<segment>/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(segment, path):
    target_base = ROUTES.get(segment)
    if not target_base:
        return jsonify(error="Unknown service"), 404

    url = f"{target_base}/api/{segment}/{path}".rstrip("/")
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        params=request.args,
        data=request.get_data(),
        timeout=10,
    )

    response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP]
    return Response(resp.content, status=resp.status_code, headers=response_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4000)))
