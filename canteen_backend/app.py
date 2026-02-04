from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ---------------- CONFIG (SQLITE ONLY) ----------------
app.config["SECRET_KEY"] = "canteen_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///canteen.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    desc = db.Column(db.String(255), default="")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Placed")

    # 🔽 PAYMENT FIELDS (NEW)
    payment_method = db.Column(db.String(20))      # COD / UPI
    payment_status = db.Column(db.String(20))      # Paid / Pending
    transaction_id = db.Column(db.String(50))      # Dummy ID

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    qty = db.Column(db.Integer, nullable=False)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return "Canteen backend running (Flask + SQLite)"

# ---------------- AUTH ----------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    if User.query.filter_by(email=data["email"]).first():
        return jsonify(success=False, message="Email already exists")

    user = User(
        name=data["name"],
        email=data["email"],
        password=generate_password_hash(data["password"]),
        role=data["role"]
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(success=True)

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"], role=data["role"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify(success=False, message="Invalid credentials")

    return jsonify(
        success=True,
        name=user.name,
        email=user.email,
        role=user.role
    )

# ---------------- MENU ----------------
@app.route("/api/menu", methods=["GET"])
def menu():
    items = MenuItem.query.all()
    return jsonify(
        success=True,
        items=[{
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "price": m.price,
            "desc": m.desc
        } for m in items]
    )

# ---------------- ADMIN MENU ----------------
@app.route("/api/admin/menu", methods=["GET", "POST"])
def admin_menu():
    if request.method == "GET":
        items = MenuItem.query.all()
        return jsonify(success=True, items=[{
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "price": m.price,
            "desc": m.desc
        } for m in items])

    data = request.get_json()
    item = MenuItem(
        name=data["name"],
        category=data["category"],
        price=float(data["price"]),
        desc=data.get("desc", "")
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(success=True)

@app.route("/api/admin/menu/<int:item_id>", methods=["PUT", "DELETE"])
def admin_menu_update(item_id):
    item = MenuItem.query.get_or_404(item_id)

    if request.method == "DELETE":
        db.session.delete(item)
        db.session.commit()
        return jsonify(success=True)

    data = request.get_json()
    item.name = data.get("name", item.name)
    item.category = data.get("category", item.category)
    item.price = float(data.get("price", item.price))
    item.desc = data.get("desc", item.desc)
    db.session.commit()

    return jsonify(success=True)

# ---------------- ORDERS (USER) ----------------
@app.route("/api/orders", methods=["POST"])
def place_order():
    data = request.get_json()
    user_email = data.get("userEmail")
    items = data.get("items", [])

    if not user_email or not items:
        return jsonify(success=False, message="Invalid order")

    order = Order(user_email=user_email, total=0, status="Placed")
    db.session.add(order)
    db.session.commit()

    total = 0
    for it in items:
        menu_item = MenuItem.query.get(it["id"])
        if not menu_item:
            continue

        qty = int(it["qty"])
        total += menu_item.price * qty

        db.session.add(OrderItem(
            order_id=order.id,
            name=menu_item.name,
            price=menu_item.price,
            qty=qty
        ))

    order.total = total
    db.session.commit()

    return jsonify(success=True, orderId=order.id)

@app.route("/api/myorders", methods=["GET"])
def my_orders():
    email = request.args.get("email")
    orders = Order.query.filter_by(user_email=email).order_by(Order.created_at.desc()).all()

    return jsonify(
        success=True,
        orders=[{
            "id": o.id,
            "total": o.total,
            "status": o.status,
            "createdAt": o.created_at.isoformat(),
            "items": [{
                "name": i.name,
                "price": i.price,
                "qty": i.qty
            } for i in OrderItem.query.filter_by(order_id=o.id).all()]
        } for o in orders]
    )

# ---------------- ORDERS (STAFF) ----------------
@app.route("/api/staff/orders", methods=["GET"])
def staff_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify(
        success=True,
        orders=[{
            "id": o.id,
            "userEmail": o.user_email,
            "total": o.total,
            "status": o.status,
            "createdAt": o.created_at.isoformat(),
            "items": [{
                "name": i.name,
                "price": i.price,
                "qty": i.qty
            } for i in OrderItem.query.filter_by(order_id=o.id).all()]
        } for o in orders]
    )

@app.route("/api/staff/orders/<int:order_id>/status", methods=["PUT"])
def update_status(order_id):
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    order.status = data["status"]
    db.session.commit()
    return jsonify(success=True)

# ---------------- INIT ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Seed default menu if empty
        if MenuItem.query.count() == 0:
            db.session.add(MenuItem(name="Veg Burger", category="Snacks", price=60, desc="Crispy veg patty"))
            db.session.add(MenuItem(name="Tea", category="Beverages", price=15, desc="Hot tea"))
            db.session.commit()

    app.run(debug=True)
