import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, symbols, get_price, get_ucash, enter_expense, get_stock, \
    get_sum_all, get_quantity, get_history

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id_user = session["user_id"]
    user_portfolio = get_stock(id_user)
    cash = get_ucash(id_user)
    print(f'PORTFOLIO')
    print(user_portfolio)
    user_actual = get_sum_all(id_user)
    return render_template("index.html", portfolio=user_portfolio, all=user_actual, cash=f'{cash:,.2f}')


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        # запрашиваем перчень компаний  через API
        companies = symbols()
        print(companies)
        return render_template("buy.html", brands=companies)
    else:
        # обрабатываем POST request из формы
        if not request.form.get("symbol"):
            return apology("You must choose company", 403)
        company_id = request.form.get("symbol")
        quantity = request.form.get("shares")
        # получение актуальной цены
        price = get_price(company_id)
        # получение Id пользователя
        print(session["user_id"])
        # id_user = db.execute("SELECT id from users WHERE username = :username", username = session["user_id"])
        id_user = session["user_id"]
        # print(id_user)
        if not id_user:
            return apology("User identity error", 403)
        # проверяем, что у пользователя достаточно средств на покупку
        expense = price * float(quantity)
        act_cash = get_ucash(id_user)
        if (act_cash - expense) > 0:
            db.execute(
                "INSERT INTO purchase ('id_user', 'company', 'count' , 'price') VALUES( :id_user, :company, :count, :price)",
                id_user=id_user, company=company_id, count=quantity, price=price)
            # уменьшаем кошелек пользователя на сумму купленных акций
            # Запись в бд
            enter_expense(id_user, -expense)
            return redirect("/")
        else:
            return apology("You don't have enough money", 403)


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get("q")
    rows = db.execute("SELECT * FROM users WHERE username = :username",
                      username=username)
    if len(rows) != 0:
        return "exist"
    else:
        return "valid"


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id_user = session["user_id"]
    user_history = get_history(id_user)
    user_actual = get_sum_all(id_user)
    print(f'HISTORY : {user_history}')
    return render_template("history.html", history=user_history, all=user_actual)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        companies = symbols()
        return render_template("quote.html", brands=companies)
    else:
        Data = lookup(request.form.get("symbol"))
        Data['price'] = usd(Data['price'])
        return render_template("quoted.html", data=Data)
    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # если запрос через форму  и сабмит
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            print(request.form.get("password"))
            return apology("must provide password", 403)
        elif not request.form.get("confirmation"):
            print(request.form.get("confirmation"))
            return apology("must provide confirmation password", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation isn't identical", 403)
        else:
            # проверем есть ли уже в системе такой пользователь
            exist = db.execute("SELECT username FROM users WHERE username = :username",
                               username=request.form.get("username"))
            print(exist)
            if len(exist) > 0:
                return apology("user with this logon name already exist", 403)
            else:
                # генерируем из пароля хэш
                psw = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=4)
                db.execute("INSERT INTO users ('username' , 'hash') VALUES(:username, :ha)",
                           username=request.form.get("username"), ha=psw)
                print(f'User created')
                return redirect("/")
    # если идет просто обращение к странице
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":
        # запрашиваем перчень компаний  через API
        companies = symbols()
        print(companies)
        return render_template("sell.html", brands=companies)
    else:
        # обрабатываем POST request из формы
        if not request.form.get("symbol"):
            return apology("You must choose company", 403)
        company_id = request.form.get("symbol")
        quantity = request.form.get("shares")
        # получение актуальной цены
        price = get_price(company_id)
        # получение Id пользователя
        print(session["user_id"])
        # id_user = db.execute("SELECT id from users WHERE username = :username", username = session["user_id"])
        id_user = session["user_id"]
        # print(id_user)
        if not id_user:
            return apology("User identity error", 403)
        # проверяем, что у пользователя достаточно средств на покупку
        quantity_my = get_quantity(id_user, company_id)
        expense = price * float(quantity)
        act_cash = get_ucash(id_user)
        # Надо проверить что у пользователя есть достаточное кол-во акций на продажу
        if (quantity_my - int(quantity)) >= 0:
            print(f'{quantity=}')
            db.execute(
                "INSERT INTO purchase ('id_user', 'company', 'count' , 'price') VALUES( :id_user, :company, :count, :price)",
                id_user=id_user, company=company_id, count=int(quantity)*(-1), price=price)
            # добавляем в  кошелек пользователя на сумму купленных акций
            # Запись в бд
            enter_expense(id_user, expense)
            return redirect("/")
        else:
            return apology("You don't have enough йгфтешен", 403)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
