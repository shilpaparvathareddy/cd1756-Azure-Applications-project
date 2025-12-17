from datetime import datetime
import string
import random

from FlaskWebProject import app, db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import flash

from azure.storage.blob import BlobServiceClient


# ==========================
# Azure Blob Configuration
# ==========================

BLOB_CONTAINER = app.config.get("BLOB_CONTAINER")
BLOB_ACCOUNT = app.config.get("BLOB_ACCOUNT")
BLOB_STORAGE_KEY = app.config.get("BLOB_STORAGE_KEY")

blob_service_client = BlobServiceClient(
    account_url=f"https://{BLOB_ACCOUNT}.blob.core.windows.net",
    credential=BLOB_STORAGE_KEY
)

container_client = blob_service_client.get_container_client(BLOB_CONTAINER)


# ==========================
# Helpers
# ==========================

def id_generator(size=32, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# ==========================
# User Model
# ==========================

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================
# Post Model
# ==========================

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    author = db.Column(db.String(75))
    body = db.Column(db.String(800))
    image_path = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Post {self.id}>'

    def save_changes(self, form, file, user_id, new=False):
        self.title = form.title.data
        self.author = form.author.data
        self.body = form.body.data
        self.user_id = user_id

        if file:
            try:
                original_filename = secure_filename(file.filename)
                extension = original_filename.rsplit('.', 1)[1]
                new_filename = f"{id_generator()}.{extension}"

                blob_client = container_client.get_blob_client(new_filename)
                blob_client.upload_blob(file, overwrite=True)

                if self.image_path:
                    try:
                        container_client.delete_blob(self.image_path)
                    except Exception:
                        pass

                self.image_path = new_filename

            except Exception as e:
                flash(f"Image upload failed: {e}")

        if new:
            db.session.add(self)

        db.session.commit()
