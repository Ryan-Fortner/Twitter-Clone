from flask import Flask, request, render_template, redirect, flash, session
from mysqlconn import connectToMySQL
from flask_bcrypt import Bcrypt
import re
from datetime import datetime, timedelta  
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

        mysql = connectToMySQL("dojo_tweets")
        query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW())"

        data = {
            'fn': request.form['fn'],
            'ln': request.form['ln'],
            'em': request.form['em'],
            'pw': hashed_pw
        }

        session['user_id'] = mysql.query_db(query, data) #Friendly login, use user_id to track user while logged in

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
        mysql = connectToMySQL('dojo_tweets')
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

@app.route('/logout')
def on_logout():
    session.clear()
    return redirect("/")

@app.route("/success")
def landing():
    if 'user_id' not in session:
        return redirect("/")
    
    mysql = connectToMySQL("dojo_tweets")
    query = "SELECT first_name FROM users WHERE user_id = %(u_id)s"
    data = {
        'u_id': session['user_id']
    }
    user_data = mysql.query_db(query, data)
    if user_data: 
        user_data = user_data[0]
    else:
        return redirect("/")

    mysql = connectToMySQL("dojo_tweets")
    query = "SELECT tweets.author, tweets.tweet_id, tweets.message, tweets.created_at, users.first_name, users.last_name FROM tweets JOIN users ON tweets.author = users.user_id"
    tweets = mysql.query_db(query)

    mysql = connectToMySQL("dojo_tweets")
    query = "SELECT tweet_like FROM users_likes WHERE user_like = %(user_id)s"
    data = {
        'user_id': session['user_id']
    }
    liked_tweets = [ tweet['tweet_like'] for tweet in mysql.query_db(query, data) ] #for loop that creates a list of all the liked tweets, also known as list comprehension 

    mysql = connectToMySQL("dojo_tweets")
    query = "SELECT tweet_like, COUNT(tweet_like) as like_count FROM users_likes GROUP BY tweet_like"
    like_count = mysql.query_db(query)

    for tweet in tweets:
        td = datetime.now() - tweet['created_at']

        if td.seconds == 0:
            tweet['time_since_secs'] = 1
        if td.seconds < 60 and td.seconds > 0:
            tweet['time_since_secs'] = td.seconds
        if td.seconds < 3600:
            tweet['time_since_minutes'] = round(td.seconds / 60)
        if td.seconds > 3600:
            tweet['time_since_hours'] = round(td.seconds / 3600)
        if td.days > 0:
            tweet['time_since_days'] = td.days
    
        for like in like_count:
            if like['tweet_like'] == tweet['tweet_id']:
                tweet['like_count'] = like['like_count']

        if 'like_count' not in tweet:
            tweet['like_count'] = 0

    return render_template("landing.html", user = user_data, tweets=tweets, liked_tweets=liked_tweets)

@app.route("/post_tweet", methods=['POST'])
def save_tweet_to_db():
    if 'user_id' not in session:
        return redirect("/")

    is_valid = True
    if len(request.form['tweet_content']) < 5:
        is_valid = False
        flash("Tweets must be at least 5 characters long.")

    if not is_valid:
        return redirect("/")

    mysql = connectToMySQL('dojo_tweets')
    query = "INSERT INTO tweets (message, author, created_at, updated_at) VALUES (%(m)s, %(a)s, NOW(), NOW())"
    data = {
        'm': request.form["tweet_content"],
        'a': session['user_id']
    }
    mysql.query_db(query, data)
    return redirect("/success")

@app.route("/tweet_detail/<t_id>")
def tweet_detail(t_id):
    mysql = connectToMySQL("dojo_tweets")
    query = "SELECT tweet_id, tweets.message, tweets.created_at, users.first_name, users.last_name FROM tweets JOIN users ON tweets.author = users.user_id WHERE tweet_id = %(t_id)s"
    data = {'t_id': t_id}
    tweet_data = mysql.query_db(query, data)

    return render_template("detail.html", tweet_data=tweet_data)

@app.route("/like_tweet/<tweet_id>")
def on_like(tweet_id):
    mysql = connectToMySQL("dojo_tweets")
    query = "INSERT INTO users_likes (user_like, tweet_like) VALUES (%(user_id)s, %(tweet_id)s)"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id 
    }
    _= mysql.query_db(query, data)
    return redirect("/success")

@app.route("/unlike_tweet/<tweet_id>")
def on_unlike(tweet_id):
    mysql = connectToMySQL("dojo_tweets")
    query = "DELETE FROM users_likes WHERE user_like = %(user_id)s AND tweet_like = %(tweet_id)s"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id 
    }
    mysql.query_db(query, data)
    return redirect("/success")

@app.route("/delete_tweet/<tweet_id>")
def on_delete(tweet_id):
    mysql = connectToMySQL("dojo_tweets")
    query = "DELETE FROM tweets WHERE tweet_id = %(t_id)s AND author = %(u_id)s"
    data = {
        't_id': tweet_id,
        'u_id':session['user_id']
    }
    mysql.query_db(query, data)
    return redirect("/success")

if __name__ == "__main__":
    app.run(debug=True)