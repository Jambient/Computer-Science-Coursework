import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from passlib.hash import sha256_crypt

from Qearn.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/')

@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        school_code = request.form["school-code"].upper()
        account_type = request.form['account-type']
        firstName = request.form['first-name']
        lastName = request.form['last-name']
        db = get_db()
        error = None

        print(email, password, school_code, account_type, firstName, lastName)

        ## check if the form is fully filled
        if not email or not password or not school_code or not account_type or not firstName or not lastName:
            return "Form has not been fully filled", 500
        
        ##validate account type
        if account_type != "student" and account_type != "teacher":
            return "Account type is not valid", 500

        ## validate school code
        db.execute("SELECT * FROM school WHERE SchoolCode = %s", (school_code,))
        school = db.fetchone()

        if not school:
            return "School Code is not valid.", 500
        
        ## create user account
        try:
            db.execute(
                "INSERT INTO user (FirstName, LastName, Email, Password, AccountType, SchoolID) VALUES (%s, %s, %s, %s, %s, %s)",
                (firstName, lastName, email, sha256_crypt.encrypt(password), account_type, school["ID"])
            )
        except db.IntegrityError:
            error = "There is already an account with that email."
        else:
            return redirect(url_for("auth.login"))

    type = request.args.get('type')
    if type == 'student' or type == 'teacher':
        return render_template("auth/register.html")
    else:
        return redirect(url_for('index'))

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None

        db.execute(
            'SELECT * FROM user WHERE Email = %s', (email,)
        )
        user = db.fetchone()

        if (user is None) or (not sha256_crypt.verify(password, user["Password"])):
            error = 'The email or password is not correct.'

        if error is None:
            session.clear()
            session['user_id'] = user['ID']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.route('/forgotpassword')
def forgot_password():
    return render_template('auth/forgotpassword.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        db.execute(
            'SELECT * FROM user WHERE ID = %s', (user_id)
        )
        g.user = db.fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view