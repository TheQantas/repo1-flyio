import secrets
from flask import Flask, request, Response, render_template, redirect, abort, flash, url_for, session
from src.model.product import Product, InventorySnapshot, db
from src.model.user import User, user_db
from src.common.forms import LoginForm
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
from flask_bcrypt import Bcrypt

app = Flask(__name__, static_url_path='', static_folder='static')

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

bcrypt = Bcrypt(app)

app.config['SECRET_KEY'] = secrets.token_urlsafe()
app.config["SESSION_PROTECTION"] = "strong"


with db:
    db.create_tables([Product, InventorySnapshot])

with user_db:
    user_db.create_tables([User])

#used by flask-login
@login_manager.user_loader
def load_user(user_id):
    user = User.get_by_uid(user_id)
    return user
# This hook ensures that a connection is opened to handle any queries
# generated by the request.
@app.before_request
def _db_connect():
    db.connect()


# This hook ensures that the connection is closed when we've finished
# processing the request.
@app.teardown_request
def _db_close(exc):
    if not db.is_closed():
        db.close()

@app.post("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    next = request.args.get('next')
    errors = [] #used to display errors on the login page
    if form.validate_on_submit(): #makes sure form is complete
        user = User.get_by_username(form.username.data)
        if user is None:
            errors.append("User not found.")
            return render_template('security/login.html', form=form, errors=errors)
        correct_password = bcrypt.check_password_hash(user.password, form.password.data)
        if not correct_password:
            errors.append("Incorrect password.")
            return render_template('security/login.html', form=form, errors=errors)
        login_success = login_user(user)
        if not login_success:
            errors.append("Login failed")
            return render_template('security/login.html', form=form, errors=errors)
        return redirect(next or url_for("home"))
    return render_template('security/login.html', form=form, errors=errors)

@app.get("/")
@login_required #any user can access home page
def home():
    # Fills the days left for each product with product.get_days_until_out
    Product.fill_days_left()
    # Loads products in urgency order
    products = Product.urgency_rank()
    return render_template("index.html", product_list=products, user=current_user)

@app.get("/inventory-history")
@login_required #any user can access inventory history
def inventory_history():
    product_id = request.args.get('product-id', None, type=int)
    if product_id is None: # TODO: have actual error page
        return abort(404, description=f"Could not find product id")

    product = Product.get_product(product_id)
    if product is None: # TODO: have actual error page
        return abort(404, description=f"Could not find product {product_id}")

    snapshots = InventorySnapshot.all_of_product(product_id)
    usage = product.get_usage_per_day()
    days_until_out = product.get_days_until_out(usage)

    return render_template(
        "inventory_history.html",
        product=product,
        snapshots=snapshots,
        snapshot_count=len(snapshots),
        daily_usage=round(usage, 1) if usage is not None else None,
        days_until_out=round(days_until_out) if days_until_out is not None else None,
    )


@app.get("/add")
@login_required
def get_add():
    #only admin can add products
    if current_user.username != 'admin':
        return abort(401, description='Only admins can add products')
    return render_template("add_form.html")


#Simple add, just adds stuff + 1 works with htmx
#TODO: make this a form
@app.route("/add", methods=["POST"])
@login_required
def add():
    #only admin can add products
    if current_user.username != 'admin':
        return abort(401, description='Only admins can add products')
    if Product.get_product(request.form.get("product_name")) is None:
        Product.add_product(request.form.get("product_name"), int(request.form.get("inventory")), float(request.form.get("price")), request.form.get("unit_type"), int(request.form.get("ideal_stock")), None)
        Product.fill_days_left()
        return redirect("/")
    else:
        abort(400)





@app.delete("/delete/<int:product_id>")
@login_required
def delete(product_id: int):
    #only admin can delete products
    #TODO: display message or page to user when encountering 401 error
    if current_user.username != 'admin':
        return abort(401, description='Only admins can delete products')
    Product.delete_product(product_id)
    products = Product.urgency_rank()
    return render_template("index.html", product_list=products, user=current_user)


@app.route("/update/inventory/<int:product_id>", methods=["PATCH"])
@login_required #any user can update inventory
def update_inventory(product_id: int):
    new_stock = request.form.get('stock', None, type=int)
    if new_stock is None or new_stock < 0:
        return abort(400, description="Stock count must be a positive integer")

    product = Product.get_product(product_id)
    if product is None:
        return abort(404, description=f"Could not find product {product_id}")

    product.update_stock(new_stock)
    return redirect("/", 303)

with app.app_context():
    if not User.get_by_username('admin'):
        User.add_user('admin', bcrypt.generate_password_hash('password'))
    if not User.get_by_username('staff'):
        User.add_user('staff', bcrypt.generate_password_hash('password'))
    if not User.get_by_username('volunteer'):
        User.add_user('volunteer', bcrypt.generate_password_hash('password'))

if __name__ == '__main__':

    app.run(port=5000, debug=True)