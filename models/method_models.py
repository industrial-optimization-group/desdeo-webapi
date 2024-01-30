import dill
from database import db

from sqlalchemy.dialects import postgresql

# to be able to serialize lambdified expressions returned by SymPy
# This might break some serializations!
dill.settings["recurse"] = True


class Method(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    method_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guest.id"), nullable=True)
    minimize = db.Column(db.String(120), nullable=False)
    # status of the method. Options: ["NOT STARTED", "ITERATING", "FINISHED"]
    status = db.Column(db.String(120), nullable=True)
    last_request = db.Column(db.PickleType(pickler=dill), nullable=True)

    def __repr__(self):
        return (
            f"Method = id:{self.id}, name:{self.name}, user_id:{self.user_id}, minimize:{self.minimize}, "
            f"status:{self.status}, last_request:{self.last_request}"
        )


class Preference(db.Model):
    """Database model for storing preferences temporarily (for UTOPIA)."""

    __tablename__ = "preference"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    method = db.Column(db.String, nullable=False)
    preference = db.Column(postgresql.JSON, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
