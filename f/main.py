#import packages
from flask import Flask, render_template, request, g, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

from sqlalchemy.orm import relationship
from sqlalchemy import or_

from hashlib import md5
import os
import datetime

#initialize flask app and database
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] =  datetime.timedelta(minutes=6)
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)

db = SQLAlchemy(app)

#define user table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), unique=False, nullable=False)
    lastname = db.Column(db.String(80), unique=False, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=True)
    is_private = db.Column(db.Boolean, default=False)
    password = db.Column(db.String(255), unique=False, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.datetime.now())
    posts = db.relationship("Post")
    follows = db.relationship("Follow")
    likes = db.relationship("Like")

    def __repr__(self) :
        return self.username

    def as_dict(self):
        dict = {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "username": self.username,
            "email": self.email,
            "created_date": self.created_date,
            "is_private": self.is_private
        }
        return dict

#define post table
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=False, nullable=False)
    text = db.Column(db.Text, unique=False, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    likes = db.relationship("Like")

    def as_dict(self):
        dict = {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "photo": self.photo,
            "user_id": self.user_id
        }
        return dict

#define follow table
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    followed_user_id = db.Column(db.Integer)
    accept = db.Column(db.String(80), default="pending")

    def __repr__(self)->str:
        return str(self.followed_user_id)

    def as_dict(self):
        dict = {
            "id": self.id,
            "user_id": self.user_id,
            "accept": self.accept,
            "followed_user_id": self.followed_user_id
        }
        return dict

#define like table
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

#create the Tables
db.create_all()

#routes

#landing page route
@app.route("/")
def index():
    session["username"] = ""
    if session["username"]:
        username = session["username"]
        g.username = username
        return redirect(url_for(".home"))

    return render_template("index.html")

#sign in route
@app.route("/signin", methods=['GET', 'POST'])
def sign_in():
    if request.method == "POST":
        email = None
        password = None
        err = None

        if "email" in request.form:
            email = request.form["email"]
            if email.strip() == "":
                err = "Email field can't be empty!"

            if "password" in request.form:
                password = request.form["password"]
                if password.strip() == "":
                    err = "Password field can't be empty!"


            hash_pass = md5(password.encode()).hexdigest()
            user = User.query.filter(User.email == email).first()

            if not user:
                err = "There is no user with this email!"

            elif hash_pass != user.password:
                err = "Wrong password!"

            if err is not None:
                return render_template("signin.html", err=err)

            if user and hash_pass == user.password:
                session["username"] = user.username
                g.username = user.username

                return redirect(url_for(".home"))

    return render_template("signin.html")

#sign up route
@app.route("/signup", methods=['GET', 'POST'])
def sign_up():
    if request.method == "POST":
        firstname = None
        lastname = None
        username = None
        email = None
        password = None
        conf_password = None
        avatar = None

        err = None

        if "firstname" in request.form:
            firstname = request.form["firstname"]
            if firstname.strip() == "":
                err = "First name field can't be empty!"

        if "lastname" in request.form:
            lastname = request.form["lastname"]
            if lastname.strip() == "":
                err = "Last name field can't be empty!"

        if "username" in request.form:
            username = request.form["username"]
            if username.strip() == "":
                err = "Username field can't be empty!"
            elif User.query.filter(User.username==username).first():
                err = "There is an account with this username!"

        if "email" in request.form:
            email = request.form["email"]
            if email.strip() == "":
                err = "Email field can't be empty!"
            elif User.query.filter(User.email==email).first():
                err = "There is an account with this email!"

        if "password" in request.form:
            password = request.form["password"]
            if password.strip() == "":
                err = "Password field can't be empty!"

        if "conf-password" in request.form:
            conf_password = request.form["conf-password"]
            if conf_password.strip() == "":
                err = "Confirmed password field can't be empty!"
        
        if password != conf_password:
            err = "Password and confirmed password doesn't match!"

        if err is not None:
            return render_template("signup.html", err=err)
        
        else:
            hash_pass = md5(password.encode()).hexdigest()
            
            user_model = User(
                firstname = firstname,
                lastname = lastname,
                username = username,
                email = email,
                password = hash_pass
            )

            db.session.add(user_model)
            db.session.commit()

            session["username"] = username
            g.username = username
                
            return redirect(url_for(".home"))

    return render_template("signup.html")

#home route
@app.route("/home", methods=['GET', 'POST'])
def home():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username
        alert = None

        user = User.query.filter(User.username==username).first()
        g.user_id = user.id
        following = Follow.query.filter(Follow.user_id==user.id).filter(Follow.accept=="accept").all()
        followed_user_list = []

        for follow in following:
            followed_user = User.query.filter(User.id==follow.followed_user_id).first()
            followed_user_list.append(followed_user)

        if followed_user_list == []:
            alert = "You don't follow anyone!"

        user_likes = user.likes

        user_like_list = [ (like.user_id, like.post_id) for like in user_likes ]

        if request.method == "POST":
            if "like" in request.form:
                post_id = request.form["like"]
                post_model = Like(
                    user_id = user.id,
                    post_id = post_id
                )

                db.session.add(post_model)
                db.session.commit()

                return redirect(url_for(".home"))

            if "unlike" in request.form:
                post_id = request.form["unlike"]

                Like.query.filter(Like.user_id==user.id).filter(Like.post_id==post_id).delete()

                db.session.commit()

                return redirect(url_for(".home"))

        return render_template("home.html", alert=alert, followed_user_list=followed_user_list, user_like_list=user_like_list)

    return redirect(url_for(".sign_in"))


#new post route
@app.route("/new-post", methods=['GET', 'POST'])
def new_post():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        title = None
        text = None
        err = None

        if request.method == "POST":
            if "title" in request.form:
                title = request.form["title"]
                if title.strip() == "":
                    err = "Title field can't be empty!"
            if "text" in request.form:
                text = request.form["text"]
                if text.strip() == "":
                    err = "Text field can't be empty!"
           
            if err is not None:
                return render_template("new-post.html", err=err)
            else:
                user_id = User.query.filter(User.username == username).first().id
                post_model = Post(
                    title = title,
                    text = text,
                    user_id = user_id
                )

                db.session.add(post_model)
                db.session.commit()
                return redirect(url_for(".home"))

        return render_template("new-post.html")

    return redirect(url_for(".sign_in"))

#dashboard route
@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        user = User.query.filter(User.username == username).first()
        user_posts = user.posts

        if request.method == "POST":
            if "post-id" in request.form:
                post_id = request.form["post-id"]
                Post.query.filter(Post.id == post_id).delete()
                db.session.commit()
                return redirect(url_for(".dashboard"))

        return render_template("dashboard.html", user_posts=user_posts)

    return redirect(url_for(".sign_in"))

#people route
@app.route("/people", methods=['GET', 'POST'])
def people():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        current_user = User.query.filter(User.username == username).first()
        users = User.query.filter(User.username != username).all()
        user_list = [ user.as_dict() for user in users ]
        followed_users = current_user.follows
        followed_users_id_list = [ (followed_user.followed_user_id, followed_user.accept) for followed_user in followed_users ]
        
        if request.method == "POST":
            if "search" in request.form:
                search_text = request.form["search"]
                search_users = User.query.filter(User.username != username).filter(or_(User.username.contains(search_text), User.firstname.contains(search_text), User.lastname.contains(search_text))).all()
                search_user_list = [ user.as_dict() for user in search_users ]
                return render_template("people.html", user_list=search_user_list,
                                 followed_users_id_list=followed_users_id_list,
                                 )
            
            if "id" in request.form:
                print("id")
                followed_user_id = request.form["id"]
                follow_model = Follow(
                    user_id = current_user.id,
                    followed_user_id = followed_user_id
                )
                db.session.add(follow_model)
                db.session.commit()
                return redirect(url_for(".people"))

            if "unfollow-id" in request.form:
                followed_user_id = request.form["unfollow-id"]
                follow = Follow.query.filter(Follow.followed_user_id == followed_user_id).delete()

                db.session.commit()
                return redirect(url_for(".people"))
            
            if "pending-id" in request.form:
                followed_user_id = request.form["pending-id"]
                follow = Follow.query.filter(Follow.followed_user_id == followed_user_id).delete()

                db.session.commit()
                return redirect(url_for(".people"))

        return render_template("people.html", user_list=user_list,
                                 followed_users_id_list=followed_users_id_list,
                                 )

    return redirect(url_for(".sign_in"))


#follow request route
@app.route("/follow-requests", methods=['GET', 'POST'])
def follow_requests():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        user_id = User.query.filter(User.username==username).first().id
        follows = Follow.query.filter(Follow.followed_user_id==user_id).filter(Follow.accept=="pending").all()
        follow_list = []
        for follow_user in follows:
            user = User.query.filter(User.id==follow_user.user_id).first()
            follow_list.append(user)

        if request.method == "POST":
            if "accept" in request.form:
                requested_user_id = request.form["accept"]
                follow = Follow.query.filter(Follow.user_id == requested_user_id).filter(Follow.followed_user_id==user_id).first()
                follow.accept = "accept"

                db.session.commit()
                return redirect(url_for(".follow_requests"))

            if "reject" in request.form:
                requested_user_id = request.form["reject"]
                follow = Follow.query.filter(Follow.user_id == requested_user_id).filter(Follow.followed_user_id==user_id).delete()

                db.session.commit()
                return redirect(url_for(".follow_requests"))

        return render_template("follow-request.html", follow_list=follow_list)

    return redirect(url_for(".sign_in"))

#following route
@app.route("/following", methods=['GET', 'POST'])
def following():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        user_id = User.query.filter(User.username==username).first().id
        follows = Follow.query.filter(Follow.user_id==user_id).filter(Follow.accept=="accept").all()
        following_user_list = []

        for follow in follows:
            user = User.query.filter(User.id==follow.followed_user_id).first()
            following_user_list.append(user)

        if request.method == "POST":
            if "unfollow-id" in request.form:
                unfollow_id = request.form["unfollow-id"]
                follow = Follow.query.filter(Follow.user_id==user_id).filter(Follow.followed_user_id==unfollow_id).delete()

                db.session.commit()

            return redirect(url_for(".following"))

        return render_template("following.html", following_user_list=following_user_list)

    return redirect(url_for(".sign_in"))

#followers route
@app.route("/followers", methods=['GET', 'POST'])
def followers():
    if "username" in session and session["username"]:
        username = session["username"]
        g.username = username

        user_id = User.query.filter(User.username==username).first().id
        followers = Follow.query.filter(Follow.followed_user_id==user_id).filter(Follow.accept=="accept").all()
        follower_user_list = []

        for follow in followers:
            user = User.query.filter(User.id==follow.user_id).first()
            follower_user_list.append(user)
        
        if request.method == "POST":
            if "remove" in request.form:
                remove_id = request.form["remove"]
                follow = Follow.query.filter(Follow.user_id==remove_id).filter(Follow.followed_user_id==user_id).delete()

                db.session.commit()

                return redirect(url_for(".followers"))

        return render_template("followers.html", follower_user_list=follower_user_list)

    return redirect(url_for(".sign_in"))    

#sign out route
@app.route("/signout")
def sign_out():
    session["username"] = ""
    return redirect(url_for(".index"))