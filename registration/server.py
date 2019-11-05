from flask import Flask, request, render_template, redirect, flash, session
from mysqlconn import connectToMySQL
from flask_bcrypt import Bcrypt
import re    
app = Flask(__name__)
app.secret_key = "FriedRice"
bcrypt = Bcrypt(app)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 


@app.route("/")
def lr_landing():
    return render_template("index.html")

@app.route("/register", methods=['POST'])
def on_register():
    is_valid = True

    if len(request.form['fn']) < 1:
        is_valid = False
        flash("First name cannot be blank.")

    if len(request.form['ln']) < 1:
        is_valid = False
        flash("Last name cannot be blank.")
        
    if len(request.form['pw']) < 1:
        is_valid = False
        flash("Password cannot be blank.")

    if request.form['pw'] != request.form['c_pw']:
        is_valid = False
        flash("Passwords don't match.")
 
    if not EMAIL_REGEX.match(request.form['em']):
        is_valid= False
        flash("Please use a valid email.")

    if not is_valid:
        return redirect("/")
    else: 
        hashed_pw = bcrypt.generate_password_hash(request.form['pw'])

        mysql = connectToMySQL("login_registration")
        query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW())"

        data = {
            'fn': request.form['fn'],
            'ln': request.form['ln'],
            'em': request.form['em'],
            'pw': hashed_pw
        }

        session['user_id'] = mysql.query_db(query, data)

        return redirect("/success")

@app.route("/login", methods=['POST'])
def on_login():
    is_valid = True

    if len(request.form['em']) < 1:
        is_valid = False
        flash("Email cannot be blank.")

    if not EMAIL_REGEX.match(request.form['em']):
        is_valid= False
        flash("Please use a valid email.")

    if is_valid:
        mysql = connectToMySQL('login_registration')
        query = "SELECT user_id, email, password FROM users WHERE email = %(em)s"
        data = {'em': request.form['em']}
        user_data = mysql.query_db(query, data)

        if user_data:
            user = user_data[0]

            if bcrypt.check_password_hash(user_data[0]['password'], request.form['pw']):
                session['user_id'] = user['user_id']
                return redirect("/success")
            else:
                flash("Password is invalid")
                return redirect("/")

        else:
            flash("Email is not valid.")
            return redirect("/")

    else:
        return redirect("/")

@app.route("/success")
def landing():
    if 'user_id' not in session:
        return redirect("/")
    
    mysql = connectToMySQL("login_registration")
    query = "SELECT first_name FROM users WHERE user_id = %(u_id)s"
    data = {
        'u_id': session['user_id']
    }
    user_data = mysql.query_db(query, data)
    if user_data: 
        user_data = user_data[0]
    else:
        return redirect("/")

    return render_template("landing.html", user = user_data)

@app.route('/logout')
def on_logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)