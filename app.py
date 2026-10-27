from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import joblib
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# LIVE NEWS VERIFICATION
from live_verifier import verify_news


app = Flask(__name__)

# --------------------------------------------------
# FLASK SECRET KEY
# --------------------------------------------------

app.secret_key = "fake-news-detector-secret-key"


# --------------------------------------------------
# LOAD ML MODEL V3
# --------------------------------------------------

MODEL_PATH = "model/fake_news_model_v3.pkl"

try:

    model = joblib.load(MODEL_PATH)

    print("===================================")
    print("MODEL LOADED SUCCESSFULLY")
    print("Model:", MODEL_PATH)
    print("===================================")

except Exception as e:

    print("===================================")
    print("MODEL LOADING ERROR")
    print(e)
    print("===================================")

    model = None


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():

    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row

    return conn


def create_database():

    conn = get_db()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # PREDICTION HISTORY TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            news TEXT NOT NULL,
            result TEXT NOT NULL,
            confidence TEXT NOT NULL,
            date_time TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# GET DASHBOARD STATISTICS
# --------------------------------------------------

def get_statistics(user_email):

    conn = get_db()

    # TOTAL
    total_predictions = conn.execute(
        """
        SELECT COUNT(*)
        FROM predictions
        WHERE user_email = ?
        """,
        (user_email,)
    ).fetchone()[0]

    # REAL
    real_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM predictions
        WHERE user_email = ?
        AND result = 'REAL'
        """,
        (user_email,)
    ).fetchone()[0]

    # FAKE
    fake_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM predictions
        WHERE user_email = ?
        AND result = 'FAKE'
        """,
        (user_email,)
    ).fetchone()[0]

    # UNCERTAIN
    uncertain_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM predictions
        WHERE user_email = ?
        AND result = 'UNCERTAIN'
        """,
        (user_email,)
    ).fetchone()[0]

    conn.close()

    return (
        total_predictions,
        real_count,
        fake_count,
        uncertain_count
    )


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        # NORMAL USER LOGIN
        if user and check_password_hash(
            user["password"],
            password
        ):

            session["logged_in"] = True
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            return redirect(url_for("home"))

        # DEMO ADMIN LOGIN
        if email == "admin@gmail.com" and password == "admin123":

            session["logged_in"] = True
            session["user_name"] = "Admin"
            session["user_email"] = email

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password"
        )

    return render_template("login.html")


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # EMPTY FIELDS
        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill all fields."
            )

        # PASSWORD CONFIRMATION
        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        # PASSWORD LENGTH
        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must contain at least 6 characters."
            )

        # HASH PASSWORD
        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    hashed_password
                )
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "register.html",
                error="Email already registered."
            )

    return render_template("register.html")


# --------------------------------------------------
# HOME / FAKE NEWS DETECTOR
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    # LOGIN CHECK
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    result = ""
    confidence = ""

    # LIVE VERIFICATION DATA
    verification = None
    verification_news = ""

    user_email = session.get("user_email")

    # --------------------------------------------------
    # NORMAL ML NEWS PREDICTION
    # --------------------------------------------------

    if request.method == "POST":

        news = request.form.get(
            "news",
            ""
        ).strip()

        # EMPTY NEWS
        if not news:

            result = "Please enter some news."

        # MINIMUM WORD CHECK
        elif len(news.split()) < 10:

            result = (
                "Please enter a complete news article "
                "(at least 10 words)."
            )

        # MODEL CHECK
        elif model is None:

            result = (
                "Model is not available. "
                "Please check the model file."
            )

        else:

            try:

                # MODEL PREDICTION
                prediction = model.predict([news])[0]

                probabilities = model.predict_proba([news])[0]

                confidence_value = (
                    max(probabilities) * 100
                )

                # DEBUG
                print("\n")
                print("===================================")
                print("        FAKE NEWS DETECTOR")
                print("===================================")

                print(
                    "USER:",
                    session.get("user_email")
                )

                print("USER NEWS:")
                print(news)

                print("-----------------------------------")

                print("MODEL PREDICTION:")
                print(prediction)

                print("-----------------------------------")

                print("MODEL CLASSES:")
                print(model.classes_)

                print("-----------------------------------")

                print("PROBABILITIES:")
                print(probabilities)

                print("-----------------------------------")

                print("CONFIDENCE:")
                print(
                    f"{confidence_value:.2f}%"
                )

                print("===================================")

                # CONFIDENCE CHECK
                if confidence_value < 60:

                    result = "UNCERTAIN"

                else:

                    result = prediction

                confidence = (
                    f"{confidence_value:.2f}%"
                )

                # SAVE HISTORY
                conn = get_db()

                conn.execute(
                    """
                    INSERT INTO predictions
                    (
                        user_email,
                        news,
                        result,
                        confidence,
                        date_time
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_email,
                        news,
                        result,
                        confidence,
                        datetime.now().strftime(
                            "%d-%m-%Y %I:%M %p"
                        )
                    )
                )

                conn.commit()
                conn.close()

            except Exception as e:

                print("===================================")
                print("PREDICTION ERROR")
                print(e)
                print("===================================")

                result = (
                    "Prediction error. Please try again."
                )


    # --------------------------------------------------
    # DASHBOARD STATISTICS
    # --------------------------------------------------

    (
        total_predictions,
        real_count,
        fake_count,
        uncertain_count
    ) = get_statistics(user_email)


    # --------------------------------------------------
    # SHOW HOME PAGE
    # --------------------------------------------------

    return render_template(
        "index.html",

        result=result,
        confidence=confidence,

        user_name=session.get("user_name"),

        total_predictions=total_predictions,
        real_count=real_count,
        fake_count=fake_count,
        uncertain_count=uncertain_count,

        verification=verification,
        verification_news=verification_news
    )


# --------------------------------------------------
# LIVE NEWS VERIFICATION
# --------------------------------------------------

@app.route(
    "/verify-news",
    methods=["GET", "POST"]
)
def verify_news_page():

    # LOGIN CHECK
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    verification = None
    verification_news = ""

    user_email = session.get("user_email")

    # --------------------------------------------------
    # VERIFY NEWS
    # --------------------------------------------------

    if request.method == "POST":

        verification_news = request.form.get(
            "news",
            ""
        ).strip()

        if not verification_news:

            verification = {
                "status": "UNCERTAIN",
                "confidence": 0,
                "message": (
                    "Please enter some news "
                    "to verify."
                ),
                "sources": []
            }

        else:

            try:

                print("\n")
                print("===================================")
                print("      LIVE NEWS VERIFICATION")
                print("===================================")

                print("USER:", user_email)

                print("NEWS:")
                print(verification_news)

                print("-----------------------------------")

                # CALL LIVE VERIFIER
                verification = verify_news(
                    verification_news
                )

                print("STATUS:")
                print(
                    verification.get(
                        "status",
                        "UNCERTAIN"
                    )
                )

                print("CONFIDENCE:")
                print(
                    verification.get(
                        "confidence",
                        0
                    )
                )

                print("===================================")

            except Exception as e:

                print("===================================")
                print("LIVE VERIFICATION ERROR")
                print(e)
                print("===================================")

                verification = {
                    "status": "UNCERTAIN",
                    "confidence": 0,
                    "message": (
                        "Live verification failed. "
                        "Please try again."
                    ),
                    "sources": []
                }


    # --------------------------------------------------
    # DASHBOARD STATISTICS
    # --------------------------------------------------

    (
        total_predictions,
        real_count,
        fake_count,
        uncertain_count
    ) = get_statistics(user_email)


    # --------------------------------------------------
    # SHOW INDEX PAGE WITH VERIFICATION
    # --------------------------------------------------

    return render_template(
        "index.html",

        result="",
        confidence="",

        user_name=session.get("user_name"),

        total_predictions=total_predictions,
        real_count=real_count,
        fake_count=fake_count,
        uncertain_count=uncertain_count,

        verification=verification,
        verification_news=verification_news
    )


# --------------------------------------------------
# HISTORY
# --------------------------------------------------

@app.route("/history")
def history():

    # LOGIN CHECK
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    conn = get_db()

    user_email = session.get("user_email")

    # GET HISTORY
    predictions = conn.execute(
        """
        SELECT *
        FROM predictions
        WHERE user_email = ?
        ORDER BY id DESC
        """,
        (user_email,)
    ).fetchall()

    conn.close()

    # STATISTICS
    (
        total_predictions,
        real_count,
        fake_count,
        uncertain_count
    ) = get_statistics(user_email)

    # SHOW HISTORY
    return render_template(
        "history.html",

        predictions=predictions,

        user_name=session.get("user_name"),

        total_predictions=total_predictions,
        real_count=real_count,
        fake_count=fake_count,
        uncertain_count=uncertain_count
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# CREATE DATABASE
# --------------------------------------------------

create_database()


# --------------------------------------------------
# START FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    print("===================================")
    print("       FAKE NEWS DETECTOR")
    print("===================================")

    print("Server starting...")

    print(
        "Open: http://127.0.0.1:5000"
    )

    print(
        "For phone: use your laptop IPv4 address with :5000"
    )

    print("===================================")

    app.run(host="0.0.0.0", port=5000, debug=True)