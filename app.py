from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)

app.secret_key = "bite_secret_key"

DATABASE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
    
def init_db():

    conn = get_db_connection()


    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            address TEXT
        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            phone TEXT,
            rating REAL DEFAULT 0,
            delivery_time TEXT,
            image TEXT,
            status TEXT DEFAULT 'Open'
        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            price REAL NOT NULL,
            image TEXT,
            availability TEXT DEFAULT 'Available',

            FOREIGN KEY (restaurant_id)
            REFERENCES restaurants(id)
        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            delivery_address TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'Pending',
            order_status TEXT DEFAULT 'Order Placed',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (restaurant_id)
            REFERENCES restaurants(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,

            FOREIGN KEY (order_id)
            REFERENCES orders(id),

            FOREIGN KEY (food_id)
            REFERENCES foods(id)
        )
    """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS reviews (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER NOT NULL,

        restaurant_id INTEGER NOT NULL,

        order_id INTEGER NOT NULL UNIQUE,

        rating INTEGER NOT NULL,

        review TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id)
            REFERENCES users(id),

        FOREIGN KEY (restaurant_id)
            REFERENCES restaurants(id),

        FOREIGN KEY (order_id)
            REFERENCES orders(id)
    )
""")

    conn.commit()
    conn.close()


@app.route("/")
def home():

    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        password = request.form["password"]
        address = request.form["address"].strip()

        if not name or not email or not phone or not password:

            flash("Please fill all required fields.", "error")

            return redirect(url_for("register"))

        conn = get_db_connection()

        # Check if email already exists
        existing_user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            flash("Email already registered. Please login.", "error")

            return redirect(url_for("login"))

        # Hash password
        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users
            (name, email, phone, password, address)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            hashed_password,
            address
        ))

        conn.commit()
        conn.close()

        flash("Registration successful! Please login.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("customer_home"))

        flash("Invalid email or password.", "error")

        return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/customer-home")
def customer_home():

    if "user_id" not in session:

        return redirect(url_for("login"))

    return render_template(
        "customer_home.html",
        user_name=session["user_name"]
    )



@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))



@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin username or password.", "error")

        return redirect(url_for("admin_login"))

    return render_template("admin_login.html")



@app.route("/admin-dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    restaurant_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM restaurants
    """).fetchone()["count"]

    food_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM foods
    """).fetchone()["count"]

    order_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """).fetchone()["count"]

    customer_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM users
    """).fetchone()["count"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        restaurant_count=restaurant_count,
        food_count=food_count,
        order_count=order_count,
        customer_count=customer_count
    )
    

@app.route("/admin-restaurants")
def admin_restaurants():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    restaurants = conn.execute("""
        SELECT *
        FROM restaurants
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_restaurants.html",
        restaurants=restaurants
    )
    
@app.route("/admin-restaurants/add", methods=["GET", "POST"])
def add_restaurant():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        name = request.form["name"].strip()
        location = request.form["location"].strip()
        rating = request.form["rating"]
        delivery_time = request.form["delivery_time"].strip()

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO restaurants
            (
                name,
                location,
                rating,
                delivery_time
            )

            VALUES (?, ?, ?, ?)
        """, (
            name,
            location,
            rating,
            delivery_time
        ))

        conn.commit()
        conn.close()

        flash("Restaurant added successfully!", "success")

        return redirect(url_for("admin_restaurants"))

    return render_template("add_restaurant.html")


@app.route("/admin-foods")
def admin_foods():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    foods = conn.execute("""
        SELECT
            foods.id,
            foods.food_name,
            foods.category,
            foods.description,
            foods.price,
            foods.availability,
            restaurants.name AS restaurant_name,
            restaurants.location AS location

        FROM foods

        JOIN restaurants
        ON foods.restaurant_id = restaurants.id

        ORDER BY foods.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_foods.html",
        foods=foods
    )
    
@app.route("/admin-foods/add", methods=["GET", "POST"])
def add_food():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    restaurants = conn.execute("""
        SELECT id, name, location
        FROM restaurants
        ORDER BY name
    """).fetchall()

    if request.method == "POST":

        restaurant_id = request.form["restaurant_id"]
        food_name = request.form["food_name"].strip()
        category = request.form["category"].strip()
        description = request.form["description"].strip()
        price = request.form["price"]
        availability = request.form["availability"]

        conn.execute("""
            INSERT INTO foods
            (
                restaurant_id,
                food_name,
                category,
                description,
                price,
                availability
            )

            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            restaurant_id,
            food_name,
            category,
            description,
            price,
            availability
        ))

        conn.commit()
        conn.close()

        flash("Food item added successfully!", "success")

        return redirect(url_for("admin_foods"))

    conn.close()

    return render_template(
        "add_food.html",
        restaurants=restaurants
    )
    
@app.route("/admin-orders")
def admin_orders():

   
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    orders = conn.execute("""
        SELECT
            orders.id AS order_id,
            users.name AS customer_name,
            users.email AS customer_email,
            restaurants.name AS restaurant_name,
            orders.total_amount,
            orders.delivery_address,
            orders.payment_method,
            orders.payment_status,
            orders.order_status,
            orders.order_date

        FROM orders

        JOIN users
        ON orders.user_id = users.id

        JOIN restaurants
        ON orders.restaurant_id = restaurants.id

        ORDER BY orders.order_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_orders.html",
        orders=orders
    )
    
@app.route("/admin-update-order/<int:order_id>", methods=["POST"])
def admin_update_order(order_id):

    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    status = request.form.get("order_status")

    allowed_statuses = [
        "Order Placed",
        "Preparing",
        "Out for Delivery",
        "Delivered"
    ]

    if status not in allowed_statuses:
        flash("Invalid order status.", "error")
        return redirect(url_for("admin_orders"))

    conn = get_db_connection()

    conn.execute("""
        UPDATE orders
        SET order_status = ?
        WHERE id = ?
    """, (
        status,
        order_id
    ))

    conn.commit()
    conn.close()

    flash("Order status updated successfully.", "success")

    return redirect(url_for("admin_orders"))

@app.route("/admin-logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("home"))



@app.route("/search")
def search():

    search_query = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()

    if not search_query:
        return redirect(url_for("customer_home"))

    conn = get_db_connection()

    # If location is selected
    if location:

        results = conn.execute("""
            SELECT
                foods.id AS food_id,
                foods.food_name,
                foods.description,
                foods.price,
                foods.category,

                restaurants.id AS restaurant_id,
                restaurants.name AS restaurant_name,
                restaurants.location,
                restaurants.rating,
                restaurants.delivery_time

            FROM foods

            JOIN restaurants
            ON foods.restaurant_id = restaurants.id

            WHERE foods.food_name LIKE ?
            AND restaurants.location = ?
            AND foods.availability = 'Available'
            AND restaurants.status = 'Open'

            ORDER BY restaurants.rating DESC
        """, (
            "%" + search_query + "%",
            location
        )).fetchall()


    else:

        results = conn.execute("""
            SELECT
                foods.id AS food_id,
                foods.food_name,
                foods.description,
                foods.price,
                foods.category,

                restaurants.id AS restaurant_id,
                restaurants.name AS restaurant_name,
                restaurants.location,
                restaurants.rating,
                restaurants.delivery_time

            FROM foods

            JOIN restaurants
            ON foods.restaurant_id = restaurants.id

            WHERE foods.food_name LIKE ?
            AND foods.availability = 'Available'
            AND restaurants.status = 'Open'

            ORDER BY restaurants.rating DESC
        """, (
            "%" + search_query + "%",
        )).fetchall()

    conn.close()

    return render_template(
        "search_results.html",
        results=results,
        search_query=search_query,
        location=location
    )
    

@app.route("/food/<int:food_id>")
def food_details(food_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    food = conn.execute("""
        SELECT
            foods.id AS food_id,
            foods.food_name,
            foods.description,
            foods.price,
            foods.category,
            restaurants.id AS restaurant_id,
            restaurants.name AS restaurant_name,
            restaurants.location,
            restaurants.rating,
            restaurants.delivery_time

        FROM foods

        JOIN restaurants
        ON foods.restaurant_id = restaurants.id

        WHERE foods.id = ?
    """, (food_id,)).fetchone()

    conn.close()

    if not food:
        return "Food not found", 404

    return render_template(
        "food_details.html",
        food=food
    )
    
    
    

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():

    if "user_id" not in session:
        return redirect(url_for("login"))

    food_id = request.form["food_id"]

    quantity = int(request.form["quantity"])

    conn = get_db_connection()

    food = conn.execute("""
        SELECT
            foods.id,
            foods.food_name,
            foods.price,
            restaurants.id AS restaurant_id,
            restaurants.name AS restaurant_name

        FROM foods

        JOIN restaurants
        ON foods.restaurant_id = restaurants.id

        WHERE foods.id = ?
    """, (food_id,)).fetchone()

    conn.close()

    if not food:
        return "Food not found", 404


    

    if "cart" not in session:
        session["cart"] = []


    cart = session["cart"]


   

    found = False

    for item in cart:

        if item["food_id"] == food["id"]:

            item["quantity"] += quantity

            found = True

            break



    if not found:

        cart.append({
            "food_id": food["id"],
            "food_name": food["food_name"],
            "restaurant_id": food["restaurant_id"],
            "restaurant_name": food["restaurant_name"],
            "price": food["price"],
            "quantity": quantity
        })


    session["cart"] = cart

    session.modified = True

    return redirect(url_for("cart"))
    

@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cart_items = session.get("cart", [])

    total = 0

    for item in cart_items:

        total += item["price"] * item["quantity"]

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )
    

@app.route("/checkout")
def checkout():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cart_items = session.get("cart", [])

    if not cart_items:
        return redirect(url_for("cart"))

    conn = get_db_connection()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    conn.close()

    subtotal = 0

    for item in cart_items:
        subtotal += item["price"] * item["quantity"]

    delivery_charge = 40

    total = subtotal + delivery_charge

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        user=user,
        subtotal=subtotal,
        delivery_charge=delivery_charge,
        total=total
    )
    

@app.route("/place-order", methods=["POST"])
def place_order():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cart_items = session.get("cart", [])

    if not cart_items:
        return redirect(url_for("cart"))

    address = request.form["address"].strip()
    payment_method = request.form["payment_method"]

    if not address:

        flash("Please enter your delivery address.", "error")

        return redirect(url_for("checkout"))

    if payment_method not in ["COD", "ONLINE"]:

        flash("Please select a payment method.", "error")

        return redirect(url_for("checkout"))

    subtotal = 0

    for item in cart_items:

        subtotal += item["price"] * item["quantity"]

    delivery_charge = 40

    total = subtotal + delivery_charge


    restaurant_id = cart_items[0]["restaurant_id"]

    conn = get_db_connection()



    if payment_method == "COD":
        payment_status = "Cash on Delivery"
        order_status = "Order Placed"

    else:
        payment_status = "Paid"
        order_status = "Order Placed"


    cursor = conn.execute("""
        INSERT INTO orders
        (
            user_id,
            restaurant_id,
            total_amount,
            delivery_address,
            payment_method,
            payment_status,
            order_status
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        restaurant_id,
        total,
        address,
        payment_method,
        payment_status,
        order_status
    ))

    order_id = cursor.lastrowid

    for item in cart_items:

        conn.execute("""
            INSERT INTO order_items
            (
                order_id,
                food_id,
                quantity,
                price
            )

            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            item["food_id"],
            item["quantity"],
            item["price"]
        ))

    conn.commit()
    conn.close()

    # Clear cart

    session["cart"] = []

    session.modified = True

    return redirect(
        url_for(
            "order_confirmation",
            order_id=order_id
        )
    )
    
    

@app.route("/order-confirmation/<int:order_id>")
def order_confirmation(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    order = conn.execute("""
        SELECT
            orders.*,
            restaurants.name AS restaurant_name,
            restaurants.delivery_time

        FROM orders

        JOIN restaurants
        ON orders.restaurant_id = restaurants.id

        WHERE orders.id = ?
        AND orders.user_id = ?
    """, (
        order_id,
        session["user_id"]
    )).fetchone()

    conn.close()

    if not order:
        return "Order not found", 404

    return render_template(
        "order_confirmation.html",
        order=order
    )
    
    
@app.route("/my-orders")
def my_orders():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    orders = conn.execute("""
        SELECT
            orders.id,
            orders.total_amount,
            orders.delivery_address,
            orders.payment_method,
            orders.payment_status,
            orders.order_status,
            orders.order_date,
            restaurants.name AS restaurant_name

        FROM orders

        JOIN restaurants
        ON orders.restaurant_id = restaurants.id

        WHERE orders.user_id = ?

        ORDER BY orders.order_date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_orders.html",
        orders=orders
    )
    
@app.route("/order-details/<int:order_id>")
def order_details(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    order = conn.execute("""
        SELECT
            orders.*,
            restaurants.name AS restaurant_name
        FROM orders
        JOIN restaurants
        ON orders.restaurant_id = restaurants.id
        WHERE orders.id = ?
        AND orders.user_id = ?
    """, (
        order_id,
        session["user_id"]
    )).fetchone()

    if not order:
        conn.close()
        return "Order not found", 404

    items = conn.execute("""
        SELECT
            order_items.quantity,
            order_items.price,
            foods.food_name,
            foods.category
        FROM order_items
        JOIN foods
        ON order_items.food_id = foods.id
        WHERE order_items.order_id = ?
    """, (order_id,)).fetchall()

    conn.close()

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )
    
    
@app.route("/explore-food")
def explore_food():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    foods = conn.execute("""
        SELECT
            foods.id AS food_id,
            foods.food_name,
            foods.description,
            foods.price,
            foods.category,
            foods.availability,
            restaurants.name AS restaurant_name,
            restaurants.location,
            restaurants.rating,
            restaurants.delivery_time

        FROM foods

        JOIN restaurants
        ON foods.restaurant_id = restaurants.id

        WHERE foods.availability = 'Available'
        AND restaurants.status = 'Open'

        ORDER BY restaurants.rating DESC
    """).fetchall()

    conn.close()

    return render_template(
        "explore_food.html",
        foods=foods
    )
    
    
@app.route("/admin-payments")
def admin_payments():

    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    payments = conn.execute("""
        SELECT
            orders.id AS order_id,
            users.name AS customer_name,
            restaurants.name AS restaurant_name,
            orders.total_amount,
            orders.payment_method,
            orders.payment_status,
            orders.order_status,
            orders.order_date

        FROM orders

        JOIN users
        ON orders.user_id = users.id

        JOIN restaurants
        ON orders.restaurant_id = restaurants.id

        ORDER BY orders.order_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_payments.html",
        payments=payments
    )
 
@app.route("/admin-customers")
def admin_customers():

    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    customers = conn.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            address
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_customers.html",
        customers=customers
    )
@app.route("/rate-order/<int:order_id>", methods=["GET", "POST"])
def rate_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    order = conn.execute("""
        SELECT
            orders.id,
            orders.restaurant_id,
            restaurants.name AS restaurant_name
        FROM orders

        JOIN restaurants
        ON orders.restaurant_id = restaurants.id

        WHERE orders.id = ?
        AND orders.user_id = ?
        AND orders.order_status = 'Delivered'
    """, (
        order_id,
        session["user_id"]
    )).fetchone()

    if not order:
        conn.close()
        return "Order not found or order is not delivered yet.", 404

    existing_review = conn.execute("""
        SELECT id
        FROM reviews
        WHERE order_id = ?
    """, (order_id,)).fetchone()

    if existing_review:
        conn.close()
        return "You have already rated this order.", 400

    if request.method == "POST":

        rating = int(request.form["rating"])

        review = request.form.get("review", "").strip()

        if rating < 1 or rating > 5:

            conn.close()

            flash("Please select a rating between 1 and 5.", "error")

            return redirect(
                url_for(
                    "rate_order",
                    order_id=order_id
                )
            )

        conn.execute("""
            INSERT INTO reviews
            (
                user_id,
                restaurant_id,
                order_id,
                rating,
                review
            )

            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            order["restaurant_id"],
            order_id,
            rating,
            review
        ))

        average_rating = conn.execute("""
            SELECT AVG(rating)
            FROM reviews
            WHERE restaurant_id = ?
        """, (
            order["restaurant_id"],
        )).fetchone()[0]

        conn.execute("""
            UPDATE restaurants
            SET rating = ?
            WHERE id = ?
        """, (
            round(average_rating, 1),
            order["restaurant_id"]
        ))

        conn.commit()
        conn.close()

        flash("Thank you! Your rating has been submitted. ⭐", "success")

        return redirect(
            url_for(
                "order_details",
                order_id=order_id
            )
        )

    conn.close()

    return render_template(
        "rate_order.html",
        order=order
    )

if __name__ == "__main__":

    init_db()

    conn = get_db_connection()

    restaurant_count = conn.execute(
        "SELECT COUNT(*) AS count FROM restaurants"
    ).fetchone()["count"]

    if restaurant_count == 0:

       

        conn.execute("""
            INSERT INTO restaurants
            (name, description, location, phone, rating, delivery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Spice Garden",
            "Authentic Indian food with rich flavours.",
            "Chennai",
            "9876543210",
            4.8,
            "25-30 mins"
        ))

        conn.execute("""
            INSERT INTO restaurants
            (name, description, location, phone, rating, delivery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Hotel Anand",
            "Delicious traditional meals and biryani.",
            "Chennai",
            "9876543211",
            4.5,
            "30-35 mins"
        ))

        conn.execute("""
            INSERT INTO restaurants
            (name, description, location, phone, rating, delivery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Royal Kitchen",
            "Premium food made with fresh ingredients.",
            "Chennai",
            "9876543212",
            4.7,
            "20-25 mins"
        ))

        conn.execute("""
            INSERT INTO restaurants
            (name, description, location, phone, rating, delivery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Urban Tadka",
            "Modern Indian cuisine for food lovers.",
            "Chennai",
            "9876543213",
            4.6,
            "25-30 mins"
        ))

        conn.commit()

        restaurants = conn.execute(
            "SELECT id, name FROM restaurants"
        ).fetchall()

        restaurant_ids = {}

        for restaurant in restaurants:
            restaurant_ids[restaurant["name"]] = restaurant["id"]


        foods = [

            (
                restaurant_ids["Spice Garden"],
                "Chicken Biryani",
                "Biryani",
                "Aromatic basmati rice with tender chicken.",
                250
            ),

            (
                restaurant_ids["Hotel Anand"],
                "Chicken Biryani",
                "Biryani",
                "Traditional South Indian style chicken biryani.",
                220
            ),

            (
                restaurant_ids["Royal Kitchen"],
                "Chicken Biryani",
                "Biryani",
                "Royal-style chicken biryani with special spices.",
                280
            ),

            (
                restaurant_ids["Urban Tadka"],
                "Chicken Biryani",
                "Biryani",
                "Flavourful biryani prepared with fresh ingredients.",
                240
            ),

            (
                restaurant_ids["Spice Garden"],
                "Margherita Pizza",
                "Pizza",
                "Classic pizza with cheese and tomato.",
                199
            ),

            (
                restaurant_ids["Urban Tadka"],
                "Veg Pizza",
                "Pizza",
                "Loaded vegetable pizza with mozzarella.",
                229
            ),

            (
                restaurant_ids["Hotel Anand"],
                "Masala Dosa",
                "South Indian",
                "Crispy dosa served with potato masala.",
                90
            ),

            (
                restaurant_ids["Spice Garden"],
                "Paneer Burger",
                "Burger",
                "Crispy paneer burger with fresh vegetables.",
                149
            ),

            (
                restaurant_ids["Royal Kitchen"],
                "Chicken Noodles",
                "Noodles",
                "Spicy chicken noodles with vegetables.",
                180
            ),

            (
                restaurant_ids["Urban Tadka"],
                "Gulab Jamun",
                "Dessert",
                "Soft and sweet traditional Indian dessert.",
                80
            )
        ]


        for food in foods:

            conn.execute("""
                INSERT INTO foods
                (restaurant_id, food_name, category, description, price)
                VALUES (?, ?, ?, ?, ?)
            """, food)


        conn.commit()

    conn.close()

    app.run(debug=True)