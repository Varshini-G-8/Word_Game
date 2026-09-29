import os
import re
import random
import string
from datetime import date, datetime

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "word-game-development-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'wordgame.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."

MAX_GUESSES = 5
MAX_WORDS_PER_DAY = 3

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="player")  # 'admin' or 'player'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(5), unique=True, nullable=False)  

class GameRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey("word.id"), nullable=False)
    play_date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(15), default="in_progress")  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="rounds")
    word = db.relationship("Word")
    guesses = db.relationship("Guess", backref="round", order_by="Guess.guess_number")

class Guess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("game_round.id"), nullable=False)
    guess_number = db.Column(db.Integer, nullable=False)
    guess_text = db.Column(db.String(5), nullable=False)
    result_pattern = db.Column(db.String(30), nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def zip_letters(guess_text, result_pattern):
    colors = result_pattern.split(",")
    return list(zip(guess_text, colors))
app.jinja_env.globals.update(zip_letters=zip_letters)

USERNAME_RE = re.compile(r"^[A-Za-z]{5,}$")

def is_valid_username(username):
    return bool(USERNAME_RE.match(username or ""))

SPECIAL_CHARS = "$%*"

def is_valid_password(password):
    if not password or len(password) < 5:
        return False
    has_alpha = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in SPECIAL_CHARS for c in password)
    return has_alpha and has_digit and has_special

def is_valid_word_guess(guess):
    return bool(re.match(r"^[A-Za-z]{5}$", guess or ""))

def score_guess(guess, answer):
    guess = guess.upper()
    answer = answer.upper()
    result = ["grey"] * 5
    answer_chars = list(answer)
    guess_chars = list(guess)

    for i in range(5):
        if guess_chars[i] == answer_chars[i]:
            result[i] = "green"
            answer_chars[i] = None
            guess_chars[i] = None

    for i in range(5):
        if guess_chars[i] is not None and guess_chars[i] in answer_chars:
            result[i] = "orange"
            idx = answer_chars.index(guess_chars[i])
            answer_chars[idx] = None

    return result

@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for("admin_home"))
        return redirect(url_for("play"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not is_valid_username(username):
            flash("Username must be at least 5 letters (upper/lower case letters only).", "error")
            return render_template("register.html", username=username)

        if not is_valid_password(password):
            flash("Password must be at least 5 characters and include a letter, a number, "
                  "and one special character ($ % *).", "error")
            return render_template("register.html", username=username)

        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("register.html", username=username)

        user = User(username=username, role="player")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", username="")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(
            username=username,
            role="player"
        ).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("play"))
        flash("Invalid player username or password.", "error")
    return render_template("player_login.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(
            username=username,
            role="admin"
        ).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin_home"))
        flash("Invalid admin username or password.", "error")
    return render_template("admin_login.html")

@app.route("/logout")
@login_required
def logout():
    was_admin = current_user.is_admin()
    logout_user()
    if was_admin:
        return redirect(url_for("admin_login"))
    return redirect(url_for("login"))

def get_or_start_round():
    """Return the user's currently in-progress round for today, or None."""
    return GameRound.query.filter_by(
        user_id=current_user.id, play_date=date.today(), status="in_progress"
    ).first()

def rounds_played_today():
    return GameRound.query.filter_by(
        user_id=current_user.id, play_date=date.today()
    ).count()

@app.route("/play")
@login_required
def play():
    if current_user.is_admin():
        return redirect(url_for("admin_home"))
    round_ = get_or_start_round()
    played_today = rounds_played_today()
    can_start_new = played_today < MAX_WORDS_PER_DAY and round_ is None
    return render_template(
        "game.html",
        round=round_,
        played_today=played_today,
        max_words_per_day=MAX_WORDS_PER_DAY,
        max_guesses=MAX_GUESSES,
        can_start_new=can_start_new,
    )

@app.route("/play/start", methods=["POST"])
@login_required
def start_round():
    if current_user.is_admin():
        return redirect(url_for("admin_home"))
    if get_or_start_round() is not None:
        return redirect(url_for("play"))
    if rounds_played_today() >= MAX_WORDS_PER_DAY:
        flash("You've reached today's limit of 3 words. Come back tomorrow!", "error")
        return redirect(url_for("play"))
    word = Word.query.order_by(db.func.random()).first()
    if not word:
        flash("No words available. Please contact the admin.", "error")
        return redirect(url_for("play"))
    round_ = GameRound(user_id=current_user.id, word_id=word.id, status="in_progress")
    db.session.add(round_)
    db.session.commit()
    return redirect(url_for("play"))

@app.route("/play/guess", methods=["POST"])
@login_required
def submit_guess():
    round_ = get_or_start_round()
    if round_ is None:
        return jsonify({"error": "No active round."}), 400
    guess_text = request.form.get("guess", "").strip().upper()
    if not is_valid_word_guess(guess_text):
        return jsonify({"error": "Enter a valid 5-letter word (letters only)."}), 400
    existing_guesses = len(round_.guesses)
    if existing_guesses >= MAX_GUESSES:
        return jsonify({"error": "No guesses remaining."}), 400
    answer = round_.word.text
    pattern = score_guess(guess_text, answer)
    guess = Guess(
        round_id=round_.id,
        guess_number=existing_guesses + 1,
        guess_text=guess_text,
        result_pattern=",".join(pattern),
    )
    db.session.add(guess)
    won = guess_text == answer
    game_over = False
    message = None
    if won:
        round_.status = "won"
        game_over = True
        message = "Congratulations! You guessed the word!"
    elif existing_guesses + 1 >= MAX_GUESSES:
        round_.status = "lost"
        game_over = True
        message = f"Better luck next time! The word was {answer}."
    db.session.commit()

    return jsonify({
        "guess": guess_text,
        "pattern": pattern,
        "game_over": game_over,
        "won": won,
        "message": message,
        "guess_number": existing_guesses + 1,
        "max_guesses": MAX_GUESSES,
    })

def admin_required():
    return current_user.is_authenticated and current_user.is_admin()

@app.route("/admin")
@login_required
def admin_home():
    if not admin_required():
        return redirect(url_for("play"))
    return render_template("admin_home.html")

@app.route("/admin/daily", methods=["GET"])
@login_required
def admin_daily_report():
    if not admin_required():
        return redirect(url_for("play"))
    day_str = request.args.get("date", date.today().isoformat())
    try:
        report_date = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        report_date = date.today()
        day_str = report_date.isoformat()
    rounds = GameRound.query.filter_by(play_date=report_date).all()
    num_users = len({r.user_id for r in rounds})
    num_correct_guesses = sum(1 for r in rounds if r.status == "won")
    num_words_attempted = len(rounds)
    return render_template(
        "admin_daily_report.html",
        report_date=day_str,
        num_users=num_users,
        num_correct_guesses=num_correct_guesses,
        num_words_attempted=num_words_attempted,
        rounds=rounds,
    )

@app.route("/admin/user", methods=["GET"])
@login_required
def admin_user_report():
    if not admin_required():
        return redirect(url_for("play"))
    username = request.args.get("username", "").strip()
    rows = []
    selected_user = None
    if username:
        selected_user = User.query.filter_by(username=username).first()
        if selected_user:
            rounds = GameRound.query.filter_by(user_id=selected_user.id).order_by(
                GameRound.play_date.desc()
            ).all()
            by_date = {}
            for r in rounds:
                d = r.play_date.isoformat()
                by_date.setdefault(d, {"words_tried": 0, "correct_guesses": 0})
                by_date[d]["words_tried"] += 1
                if r.status == "won":
                    by_date[d]["correct_guesses"] += 1
            rows = sorted(by_date.items(), key=lambda kv: kv[0], reverse=True)
        else:
            flash(f"No user found with username '{username}'.", "error")
    all_players = User.query.filter_by(role="player").order_by(User.username).all()
    return render_template(
        "admin_user_report.html",
        username=username,
        selected_user=selected_user,
        rows=rows,
        all_players=all_players,
    )

SEED_WORDS = [
    "APPLE", "BRAVE", "CHAIR", "DANCE", "EAGLE",
    "FLAME", "GRAPE", "HOUSE", "IVORY", "JOKER",
    "KNIFE", "LEMON", "MANGO", "NURSE", "OCEAN",
    "PLANT", "QUEEN", "RIVER", "STONE", "TIGER",
]

def init_db():
    with app.app_context():
        db.create_all()
        if Word.query.count() == 0:
            for w in SEED_WORDS:
                db.session.add(Word(text=w))
            db.session.commit()
            print(f"Seeded {len(SEED_WORDS)} words.")
        if User.query.filter_by(role="admin").count() == 0:
            admin = User(username="AdminUser", role="admin")
            admin.set_password(
                os.environ.get("ADMIN_PASSWORD", "Admin$123")
            )
            db.session.add(admin)
            db.session.commit()
            print("Created default admin -> username: AdminUser  password: Admin$123")
            print("IMPORTANT: change this password after first login (see README).")

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
