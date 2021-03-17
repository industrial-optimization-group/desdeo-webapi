import dill
from app import db

from models.user_models import UserModel

# to be able to serialize lambdified expressions returned by SymPy
# This might break some serializations!
dill.settings["recurse"] = True


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    problem_type = db.Column(db.String(120), nullable=False)
    problem_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    minimize = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"Problem('{self.name}', '{self.problem_type}', '{self.owner}', '{self.minimize}'')"
