import dill
from app import db

# to be able to serialize lambdified expressions returned by SymPy
# This might break some serializations!
dill.settings["recurse"] = True


class Method(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    method_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    minimize = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"Method = id:{self.id}, name:{self.name}, user_id:{self.user_id}, minimize:{self.minimize}"
