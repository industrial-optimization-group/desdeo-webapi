import dill
from sqlalchemy.orm import validates, Mapped

from sqlalchemy.dialects import postgresql

from database import db

# to be able to serialize lambdified expressions returned by SymPy
# This might break some serializations!
dill.settings["recurse"] = True

class GuestProblem(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    problem_type = db.Column(db.String(120), nullable=False)
    problem_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("guest.id"), nullable=False)
    minimize = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"Problem('{self.name}', '{self.problem_type}', '{self.owner}', '{self.minimize}'')"

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    problem_type = db.Column(db.String(120), nullable=False)
    problem_pickle = db.Column(db.PickleType(pickler=dill))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    minimize = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"Problem('{self.name}', '{self.problem_type}', '{self.owner}', '{self.minimize}'')"


class SolutionArchive(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"), nullable=False)
    solutions_dict_pickle = db.Column(db.PickleType(pickler=dill))
    meta_data = db.Column(db.String(2000), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    @validates("solutions_dict_pickle")
    def validate_dict(self, _, dict_):
        if not isinstance(dict_, dict):
            raise ValueError(
                f"A dictionary must be supplied to SolutionArchive. Type of data suplied f{type(dict_)}"
            )
        if "variables" not in dict_ or "objectives" not in dict_:
            raise ValueError(
                "The dictrionary supplied to SolutionArchive must contain the keys 'variables' and 'objectives'"
            )
        return dict_


class UTOPIASolutionArchive(db.Model):
    __tablename__ = "UTOPIAsolutionarchive"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"), nullable=False)
    preference = db.Column(db.Integer, db.ForeignKey("preference.id"), nullable=False)
    method_name=db.Column(db.String(100), nullable=False)
    objectives = db.Column(postgresql.ARRAY(db.Float), nullable=False)
    variables = db.Column(postgresql.ARRAY(db.Float), nullable=True)
    saved = db.Column(db.Boolean, nullable=False)
    current = db.Column(db.Boolean, nullable=False)
    chosen = db.Column(db.Boolean, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
