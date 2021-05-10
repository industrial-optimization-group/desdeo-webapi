import json

import dill
import numpy as np
import pandas as pd
from desdeo_problem.Objective import _ScalarObjective
from desdeo_problem.Problem import DiscreteDataProblem
from desdeo_problem.surrogatemodels.lipschitzian import LipschitzianRegressor
from desdeo_problem.Variable import Variable

from app import db
from models.problem_models import Problem as ProblemModel
from models.user_models import UserModel

dill.settings["recurse"] = True

db.create_all()


def main():
    add_user("guy", "fiery")
    add_sus_problem("guy")


def add_user(username, password):
    db.session.add(UserModel(username=username, password=UserModel.generate_hash(password)))
    db.session.commit()


def add_sus_problem(username):
    user_query = UserModel.query.filter_by(username=username).first()
    if user_query is None:
        print(f"USername {username} not found")
        return
    else:
        id = user_query.id

    file_name = "./data/approximationPF_Sustainability_MOP_Finland.csv"

    data = pd.read_csv(file_name)
    # minus because all are to be maximized
    data[["social", "economic", "environmental"]] = -data[["social", "economic", "environmental"]]

    var_names = [f"x{i}" for i in range(1, 12)]

    ideal = data[["social", "economic", "environmental"]].min().values
    nadir = data[["social", "economic", "environmental"]].max().values

    # define the sus problem
    var_names = [f"x{i}" for i in range(1, 12)]
    obj_names = ["social", "economic", "environmental"]

    problem = DiscreteDataProblem(data, var_names, obj_names, ideal, nadir)

    db.session.add(
        ProblemModel(
            name="Sustainability problem",
            problem_type="discrete",
            problem_pickle=problem,
            user_id=id,
            minimize=json.dumps([-1, -1, -1]),
        )
    )
    db.session.commit()
    print(f"Sustainability problem added for user '{username}'")


if __name__ == "__main__":
    main()
