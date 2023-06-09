from database import db
from passlib.hash import pbkdf2_sha256 as sha256


class GuestUserModel(db.Model):
    """this model describes a guest user account with no password and no possibility to store anything on the database.
    Available prblems are pre-loaded and cannot be changed."""
    __tablename__ = "guest"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    problems = db.relationship("GuestProblem", backref="owner", lazy=True)
    
    def __repr__(self):
        return f"Guest: ('{self.username}')"

class UserModel(db.Model):
    """This model describes a registered user with a password and stored problems."""
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    problems = db.relationship("Problem", backref="owner", lazy=True)

    def __repr__(self):
        return f"User: ('{self.username}')"

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def return_all(cls):
        def to_json(x):
            return {
                "username": x.username,
                "password": x.password,
            }

        return {"users": list(map(lambda x: to_json(x), UserModel.query.all()))}

    @classmethod
    def delete_all(cls):
        try:
            num_rows_deleted = db.session.query(cls).delete()
            db.session.commit()
            return {"message": f"{num_rows_deleted} row(s) deleted."}

        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": "Something went wrong"}

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hash):
        return sha256.verify(password, hash)


class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
