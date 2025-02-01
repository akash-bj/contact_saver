from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import vobject  # For vCard parsing

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    contacts = db.relationship('Contact', backref='user', lazy=True)

# Contact model
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes
@app.route("/")
@login_required
def index():
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", contacts=contacts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password, method='sha256')

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/add", methods=["POST"])
@login_required
def add_contact():
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")

    if name and phone:
        new_contact = Contact(name=name, phone=phone, email=email, user_id=current_user.id)
        db.session.add(new_contact)
        db.session.commit()
        flash("Contact added successfully!")
    else:
        flash("Name and phone are required.")

    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
@login_required
def upload_contacts():
    if 'vcard' not in request.files:
        flash("No file uploaded.")
        return redirect(url_for("index"))

    file = request.files['vcard']
    if file.filename == '':
        flash("No file selected.")
        return redirect(url_for("index"))

    try:
        vcard_data = file.read().decode('utf-8')
        vcards = vcard_data.split("BEGIN:VCARD")  # Split the file into individual vCards

        count = 0
        for vcard_str in vcards:
            if not vcard_str.strip():  # Skip empty entries
                continue

            vcard = vobject.readOne("BEGIN:VCARD" + vcard_str)  # Re-add the BEGIN:VCARD tag
            name = vcard.fn.value if hasattr(vcard, 'fn') else "Unknown"
            phone = vcard.tel.value if hasattr(vcard, 'tel') else ""
            email = vcard.email.value if hasattr(vcard, 'email') else ""

            new_contact = Contact(name=name, phone=phone, email=email, user_id=current_user.id)
            db.session.add(new_contact)
            count += 1

        db.session.commit()
        flash(f"{count} contacts uploaded successfully!")
    except Exception as e:
        flash(f"Error processing vCard file: {str(e)}")

    return redirect(url_for("index"))

@app.route("/delete/<int:contact_id>")
@login_required
def delete_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if contact.user_id == current_user.id:
        db.session.delete(contact)
        db.session.commit()
        flash("Contact deleted successfully!")
    else:
        flash("You are not authorized to delete this contact.")

    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
