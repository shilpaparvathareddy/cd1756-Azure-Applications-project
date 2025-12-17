
from flask import render_template, flash, redirect, request, session, url_for
from werkzeug.urls import url_parse
from flask_login import (
    current_user, login_user, logout_user, login_required
)
from FlaskWebProject import app, db
from FlaskWebProject.forms import LoginForm, PostForm
from FlaskWebProject.models import User, Post
import msal
import uuid
from config import Config

imageSourceUrl = (
    f"https://{app.config['BLOB_ACCOUNT']}.blob.core.windows.net/"
    f"{app.config['BLOB_CONTAINER']}/"
)


@app.route("/")
@app.route("/home")
@login_required
def home():
    posts = Post.query.all()
    return render_template("index.html", posts=posts)


@app.route("/new_post", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post()
        post.save_changes(
            form,
            request.files.get("image_path"),
            current_user.id,
            new=True
        )
        return redirect(url_for("home"))
    return render_template(
        "post.html",
        title="Create Post",
        form=form,
        imageSource=imageSourceUrl
    )


@app.route("/post/<int:id>", methods=["GET", "POST"])
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.save_changes(
            form,
            request.files.get("image_path"),
            current_user.id
        )
        return redirect(url_for("home"))
    return render_template(
        "post.html",
        title="Edit Post",
        form=form,
        imageSource=imageSourceUrl
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data
        ).first()

        if not user or not user.check_password(form.password.data):
            app.logger.warning("Invalid login attempt")
            flash("Invalid username or password")
            return redirect(url_for("login"))

        login_user(user)
        app.logger.info("admin logged in successfully")

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("home")
        return redirect(next_page)

    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=Config.SCOPE, state=session["state"])
    return render_template("login.html", form=form, auth_url=auth_url)


@app.route(Config.REDIRECT_PATH)
def authorized():
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("login"))

    if "error" in request.args:
        return render_template("auth_error.html", result=request.args)

    if "code" in request.args:
        cache = msal.SerializableTokenCache()
        msal_app = _build_msal_app(cache=cache)
        result = msal_app.acquire_token_by_authorization_code(
            request.args["code"],
            scopes=Config.SCOPE,
            redirect_uri=url_for("authorized", _external=True),
        )

        user = User.query.filter_by(username="admin").first()
        login_user(user)

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        Config.CLIENT_ID,
        authority=authority or Config.AUTHORITY,
        client_credential=Config.CLIENT_SECRET,
        token_cache=cache,
    )

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state,
        redirect_uri=url_for("authorized", _external=True),
    )
