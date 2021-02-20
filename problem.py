from desdeo_problem import MOProblem, Variable, _ScalarObjective
import numpy as np
from app import db  # noqa 401 / to fix cyclic imports
from models.user_models import UserModel
from models.problem_models import Problem


def objective_1(x):
    x = np.atleast_2d(x)
    return x[:, 0] - x[:, 1]


def objective_2(x):
    x = np.atleast_2d(x)
    return x[:, 0] + x[:, 1]


objective_1 = _ScalarObjective("objective 1", objective_1)
objective_2 = _ScalarObjective("objective 2", objective_2)

objectives = [objective_1, objective_2]

variable_1 = Variable("x_1", 0, -5, 5)
variable_2 = Variable("x_2", 0, -3, 3)

variables = [variable_1, variable_2]

problem = MOProblem(objectives, variables)
# print(problem.evaluate(np.array([[-1, 1], [-2, 2]])).objectives)

user = UserModel.query.filter_by(username="user").first()

pickled_1 = Problem.query.filter_by(user_id=user.id)[0]
pickled_2 = Problem.query.filter_by(user_id=user.id)[1]
print(pickled_1.problem_pickle.evaluate([[-1, 1], [-2, 2]]).objectives)
print(pickled_2.problem_pickle.evaluate([[-1, 1], [-2, 2]]).objectives)
