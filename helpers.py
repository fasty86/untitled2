import os
import requests
import urllib.parse

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote"
                                f"?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        print(response)
        quote = response.json()
        print(quote)
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


# возвращаем пречень символов с названиями  релевантных им компаний
def symbols():
    company_list = ['AAPL', 'NFLX', 'AA', 'AAL', 'BA', 'BABA']
    lst = {}
    for company in company_list:
        # Contact API
        try:
            api_key = os.environ.get("API_KEY")
            response = requests.get(
                f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(company)}/quote?token={api_key}")
            response.raise_for_status()
        except requests.RequestException:
            return None

        # Parse response
        try:
            quote = response.json()
            lst[company] = quote["companyName"]
        except (KeyError, TypeError, ValueError):
            return None
    return lst


def get_price(name):
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(
            f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(name)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

        # Parse response
    try:
        quote = response.json()
        return quote["latestPrice"]
    except (KeyError, TypeError, ValueError):
        return None


""" Функции для работы с БД """
db = SQL("sqlite:///finance.db")


# получение актуального состояния кошелька
def get_ucash(id_user):
    cash = db.execute("SELECT cash FROM users where id = :user_id", user_id=id_user)
    return cash[0]['cash']


#  уменьшаем  сумму на счете  на величину купленных акций
def enter_expense(id_user, expense):
    actual_cash = get_ucash(id_user)
    result = actual_cash + expense
    # делаем запись в БД
    db.execute("UPDATE users SET cash = :result WHERE id = :user_id", result=result, user_id=id_user)


# получаем данные для  index.html
def get_stock(id_user):
    data = db.execute("SELECT * FROM v_stock where id = :user_id", user_id=id_user)
    for row in data:
        for key, value in row.items():
            print(f'{key} : {value}')
        # получаем актуальную стоимость от сервиса через API
        row['current_price'] = get_price(row['company'])
        print(f"current price : {row['current_price']}")
    return data


def get_sum_all(id_user):
    """ получение общей суммыф активов пользователя"""
    # сделаем запрос из бд для подсчета  общей суммы
    calc_data = db.execute(
        "SELECT distinct coalesce(u.cash + p.cash, 0) cash FROM users u JOIN (select id_user, SUM(count * price) cash FROM "
        "purchase GROUP BY id_user ) p on u.id = p.id_user join purchase where u.id = :user_id;",
        user_id=id_user)
    if len(calc_data) !=0:
        calc_sum = calc_data[0]['cash']
        print(f" calc_sum : {calc_sum:,.2f}")
        return f'{calc_sum:,.2f}'
    else:
        return 0
