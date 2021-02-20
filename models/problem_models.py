from app import db
import dill


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    problem_type = db.Column(db.String(120), nullable=False)
    problem_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"Problem('{self.name}', '{self.problem_type}')"
