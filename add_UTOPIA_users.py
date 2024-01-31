import argparse
import csv
import json
import random
import string


import numpy as np
import pandas as pd
from desdeo_problem.problem import _ScalarObjective
from desdeo_problem.problem import DiscreteDataProblem
from desdeo_problem.surrogatemodels.lipschitzian import LipschitzianRegressor
from desdeo_problem.problem import Variable
from desdeo_problem.testproblems import river_pollution_problem

from app import app, db
from models.problem_models import Problem as ProblemModel
from models.user_models import UserModel

import pandas as pd


# db.init_app(app)

with app.app_context():
    db.drop_all()
    db.create_all()


def main():
    with app.app_context():
        letters = string.ascii_lowercase

        # UTOPIA specific stuff

        TOTAL_DMs = 100

        usernames = [
            "Philip",
            "Mari",
            "Mikko",
            "Jouni",
            "Teppo",
            "Jukka",
        ] + [f"User{i}" for i in range(1, TOTAL_DMs + 1)]
        passwords = [
            ("".join(random.choice(letters) for i in range(6)))
            for j in range(len(usernames))
        ]

        try:
            for i, (username, password) in enumerate(zip(usernames, passwords)):
                add_user(username, password)
                add_UTOPIA_problem(username, f"{(i%5) + 1}")
        except Exception as e:
            print("something went wrong...")
            print(e)
            exit()

        users_pass_hold = pd.DataFrame(
            {
                "username": usernames,
                "password": passwords,
                "Holding": [(i % 5) + 1 for i in range(len(usernames))],
            }
        )

        users_pass_hold.to_csv("./users_and_pass.csv", index=False)

        print(f"Added users {usernames} to the database succesfully.")


def add_user(username, password):
    with app.app_context():
        db.session.add(
            UserModel(username=username, password=UserModel.generate_hash(password))
        )
        db.session.commit()


def add_sus_problem(username):
    with app.app_context():
        user_query = UserModel.query.filter_by(username=username).first()
        if user_query is None:
            print(f"USername {username} not found")
            return
        else:
            id = user_query.id

        file_name = "./tests/data/sustainability_spanish.csv"

        data = pd.read_csv(file_name)
        # minus because all are to be maximized
        data[["social", "economic", "environmental"]] = -data[
            ["social", "economic", "environmental"]
        ]

        var_names = [f"x{i}" for i in range(1, 12)]

        ideal = data[["social", "economic", "environmental"]].min().values
        nadir = data[["social", "economic", "environmental"]].max().values

        # define the sus problem
        var_names = [f"x{i}" for i in range(1, 12)]
        obj_names = ["social", "economic", "environmental"]

        problem = DiscreteDataProblem(data, var_names, obj_names, ideal, nadir)

        db.session.add(
            ProblemModel(
                name="Spanish sustainability problem",
                problem_type="Discrete",
                problem_pickle=problem,
                user_id=id,
                minimize=json.dumps([-1, -1, -1]),
            )
        )
        db.session.commit()
        print(f"Sustainability problem added for user '{username}'")


def add_river_problem(username):
    with app.app_context():
        user_query = UserModel.query.filter_by(username=username).first()
        if user_query is None:
            print(f"USername {username} not found")
            return
        else:
            id = user_query.id

    problem = river_pollution_problem()
    problem.ideal = np.array([-6.34, -3.44, -7.5, 0, 0])
    problem.nadir = np.array([-4.75, -2.85, -0.32, 9.70, 0.35])

    db.session.add(
        ProblemModel(
            name="River pollution problem",
            problem_type="Analytical problem",
            problem_pickle=problem,
            user_id=id,
            minimize=json.dumps(problem._max_multiplier.tolist()),
        )
    )
    db.session.commit()
    print(f"River pollution problem added for user '{username}'")


def add_UTOPIA_problem(username, filename):
    with app.app_context():
        user_query = UserModel.query.filter_by(username=username).first()
        if user_query is None:
            print(f"USername {username} not found")
            return
        else:
            id = user_query.id

        with open("./UTOPIAData/all_solutions.json") as f:
            data = json.load(f)

        data = data[filename]

        data_npv = pd.DataFrame.from_dict(
            data["npv"], orient="index", columns=["Forest value in Euros"]
        )

        data_stock = pd.DataFrame.from_dict(
            data["stock"], orient="index", columns=["Stock in cubic meters"]
        )
        data_harvest = pd.DataFrame.from_dict(
            data["harvest_value"], orient="index", columns=["Harvest value in Euros"]
        )

        data = -pd.concat([data_npv, data_stock, data_harvest], axis=1).reset_index(
            drop=True
        )

        var_name = ["Dummy Variable"]
        ideal = data.min().values
        nadir = data.max().values

        # define the sus problem
        obj_names = data.columns.tolist()
        data[var_name] = 0

        problem = DiscreteDataProblem(data, var_name, obj_names, ideal, nadir)

        db.session.add(
            ProblemModel(
                name=f"UTOPIA problem for Holding {filename}",
                problem_type="Discrete",
                problem_pickle=problem,
                user_id=id,
                minimize=json.dumps([-1, -1, -1]),
            )
        )
        db.session.commit()
        print(f"UTOPIA problem (Holding {filename}) added for user '{username}'")


if __name__ == "__main__":
    main()
