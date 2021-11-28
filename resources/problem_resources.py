import numpy as np
import pandas as pd
import simplejson as json
from app import db
from desdeo_problem import (
    DiscreteDataProblem,
    MOProblem,
    Variable,
    _ScalarObjective,
    classificationPISProblem,
)
from desdeo_tools.maps import classificationPIS
from desdeo_tools.scalarization import AUG_GUESS_GLIDE, AUG_STOM_GLIDE
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.problem_models import Problem
from models.user_models import UserModel
from utilities.expression_parser import numpify_expressions

# The vailable problem types
available_problem_types = ["Analytical", "Discrete", "Classification PIS"]
supported_analytical_problem_operators = ["+", "-", "*", "/"]

# Problem creation base parser
problem_base_parser = reqparse.RequestParser()
problem_base_parser.add_argument(
    "problem_type",
    type=str,
    help=f"The problem type is required and must be one of {available_problem_types}",
    required=True,
)
problem_base_parser.add_argument(
    "name",
    type=str,
    help="The problem name is required",
    required=True,
)

# Analytical problem parser
problem_analytical_parser = problem_base_parser.copy()
problem_analytical_parser.add_argument(
    "objective_functions",
    type=str,
    help=(
        f"If specifying an analytical problem, please provide expressions for each objective function as a string in"
        f"a list of strings."
        f"Supported operators: {supported_analytical_problem_operators}"
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "objective_names",
    type=str,
    help=(
        "If specifying an analytical problem, please provide names for each objective function as a string in"
        "a list of strings."
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "variables",
    type=str,
    help=(
        "If specifying an analytical problem, please define the variable symbols as a list of strings."
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "variable_names",
    type=str,
    help=(
        "If specifying an analytical problem, please define the variable variable as a list of strings."
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "variable_initial_values",
    type=str,
    help=(
        "If specifying an analytical problem, please define the variable initial values as a list of floats."
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "variable_bounds",
    type=str,
    help=(
        "If specifying an analytical problem, please define the variable bounds as a list of tuples of the form"
        "['lower_bound', 'upper_bound']."
    ),
    required=True,
    action="append",
)
problem_analytical_parser.add_argument(
    "ideal",
    type=str,
    help=("The ideal point of the multiobjective optimization problem."),
    required=False,
    action="append",
)
problem_analytical_parser.add_argument(
    "nadir",
    type=str,
    help=("The nadir point of the multiobjective optimization problem."),
    required=False,
    action="append",
)
problem_analytical_parser.add_argument(
    "minimize",
    type=str,
    help=(
        "A list of either 1's or -1's depending whether an objective is to be minimized or maximized. Defaults to all"
        "objectives to be minimized."
    ),
    required=False,
    action="append",
)

# Discrete problem parser
problem_discrete_parser = problem_analytical_parser.copy()
[
    problem_discrete_parser.remove_argument(arg_name)
    for arg_name in [
        "objective_functions",
        "variable_initial_values",
        "variable_bounds",
    ]
]
problem_discrete_parser.add_argument(
    "objectives",
    type=str,
    help=(
        "When specifying a discrete problem, the objective values must be supplied as a 2D "
        "list with each objective vector on its own row."
    ),
    required=True,
    action="append",
)


# Problem access parser
problem_access_parser = reqparse.RequestParser()
problem_access_parser.add_argument(
    "problem_id",
    type=int,
    help="Specify the id of the problem to be accessed.",
    required=True,
)


class ProblemAccess(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        # TODO: remove try catch block and check the problems query
        try:
            problems = Problem.query.filter_by(user_id=current_user_id).all()

            response = {
                "problems": [
                    {
                        "id": problem.id,
                        "name": problem.name,
                        "problem_type": problem.problem_type,
                    }
                    for problem in problems
                ]
            }

            return response, 200
        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": "Could not fetch problems!"}, 404

    @jwt_required()
    def post(self):
        """Fetch a problem from the DB with a given id 'problem_id'.

        Returns:
            (tuple): tuple containing:
                (dict): A dict with fields describing the fetched problem or message
                    explaining a failure to fetch the problem.
                (int): HTTP status code: 200 if problem is found.
        """
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        data = problem_access_parser.parse_args()

        problem_query = Problem.query.filter_by(
            user_id=current_user_id, id=data["problem_id"]
        ).first()

        if not problem_query:
            # problem not found, 404
            return {"message": f"Problem with id {data['problem_id']} not found"}, 404

        try:
            # from model
            problem_id = problem_query.id
            minimize = problem_query.minimize
            problem_name = problem_query.name
            problem_type = problem_query.problem_type

            problem_pickle = problem_query.problem_pickle

            if isinstance(problem_pickle, MOProblem):
                # from MOProblem
                objective_names = problem_pickle.get_objective_names()
                variable_names = problem_pickle.get_variable_names()
                ideal = problem_pickle.ideal.tolist()
                nadir = problem_pickle.nadir.tolist()
                n_objectives = problem_pickle.n_of_objectives
            elif isinstance(problem_pickle, DiscreteDataProblem):
                # from discrete problem
                objective_names = problem_pickle.objective_names
                variable_names = problem_pickle.variable_names
                ideal = problem_pickle.ideal.tolist()
                nadir = problem_pickle.nadir.tolist()
                n_objectives = problem_pickle.n_of_objectives
            else:
                # problem type not found
                return {
                    "message": f"Problem of type {type(problem_pickle)} not found"
                }, 404

            response = {
                "objective_names": objective_names,
                "variable_names": variable_names,
                "ideal": ideal,
                "nadir": nadir,
                "n_objectives": n_objectives,
                "minimize": json.loads(minimize),
                "problem_name": problem_name,
                "problem_type": problem_type,
                "problem_id": problem_id,
            }

            # all ok, 200
            return response, 200

        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": "Encountered internal error while fetching problem"}, 500


class ProblemCreation(Resource):
    @jwt_required()
    def get(self):
        """Return the names of the available problem types that may be defined.

        Returns:
            (tuple): a tuple containing:
                (dict): a dictionary with the entry 'available_problem_types' with a list of str
                    names of the types.
                (int): HTTP status code: 200 if successful.
        """
        response = {
            "available_problem_types": available_problem_types,
        }
        return response, 200

    @jwt_required()
    def post(self):
        """Specify and add a problem to the DB.

        Returns:
            (tuple): a tuple containing:
                (dict): a dict with various entries.
                (int): HTTP status code: 201 if problem added successfully.
        """
        data = problem_base_parser.parse_args()

        if data["problem_type"] not in available_problem_types:
            # check that problem type is valid, if not, return 406
            return {
                "message": f"The problem type must be one of {available_problem_types}"
            }, 406

        if data["problem_type"] == "Analytical" or "Classification PIS":
            # handle analytical problem case
            data = problem_analytical_parser.parse_args()
            if data["objective_functions"] is None:
                # no objective functions given
                return {
                    "message": "When specifying an analytical problem, objective function expressions are required"
                }, 406
            if data["objective_names"] is None:
                # if no names given, go with default names
                objective_names = [
                    f"f_{i+1}" for i in range(len(data["objective_functions"]))
                ]

            elif len(data["objective_names"]) != len(data["objective_functions"]):
                msg = "Bad number of objective function names given."
                return {"message": msg}, 406

            else:
                objective_names = data["objective_names"]

            if data["variables"] is None:
                return {
                    "message": "When specifying an analytical problem, variable names must be specified"
                }, 406

            if data["variable_names"] is None:
                variable_names = [f"var_{i+1}" for i in range(len(data["variables"]))]

            elif len(data["variable_names"]) != len(data["variables"]):
                msg = "Bad number of variable names given."
                return {"message": msg}, 406

            else:
                variable_names = data["variable_names"]

            if data["variable_initial_values"] is None or len(
                data["variable_initial_values"]
            ) != len(data["variables"]):
                msg = "Bad number of initial variable values given"
                return {"message": msg}, 406

            if data["ideal"] is None:
                if data["problem_type"] == "Classification PIS":
                    msg = "Ideal point required to create the PIS"
                    return {"message": msg}, 406
                ideal = None

            elif len(data["ideal"]) != len(data["objective_functions"]):
                msg = "Ideal point has wrong number of components"
                return {"message": msg}, 406
            else:
                ideal = np.array(data["ideal"]).astype(float)

            if data["nadir"] is None:
                if data["problem_type"] == "Classification PIS":
                    msg = "Nadir point required to create the PIS"
                    return {"message": msg}, 406
                nadir = None
            elif len(data["nadir"]) != len(data["objective_functions"]):
                msg = "Nadir point has wrong number of components"
                return {"message": msg}, 406
            else:
                nadir = np.array(data["nadir"]).astype(float)

            if data["minimize"] is None:
                minimize = [1 for i in range(len(data["objective_functions"]))]
            elif len(data["minimize"]) != len(data["objective_functions"]):
                msg = "minimize has a wrong number of components"
                return {"message": msg}, 406
            else:
                minimize = list(map(int, data["minimize"]))

            # TODO: validate objective functions
            objective_functions_str = data["objective_functions"]
            variables_str = data["variables"]
            variable_bounds_str = data["variable_bounds"]

            if variable_bounds_str is None or len(variable_bounds_str) != len(
                variables_str
            ):
                return {"message": "Bad number of variable bounds tuples given"}, 406

            # convert the bounds and initial values to a numpy array
            variable_bounds = np.array(list(map(json.loads, variable_bounds_str)))
            variable_initial_values = np.array(data["variable_initial_values"]).astype(
                float
            )

            objective_evaluators = numpify_expressions(
                objective_functions_str, variables_str
            )

            objectives = [
                _ScalarObjective(objective_names[i], evaluator)
                for (i, evaluator) in enumerate(objective_evaluators)
            ]

            variables = [
                Variable(
                    variable_names[i],
                    variable_initial_values[i],
                    variable_bounds[i][0],
                    variable_bounds[i][1],
                )
                for i, x in enumerate(variables_str)
            ]

            if data["problem_type"] == "Analytical":
                problem = MOProblem(objectives, variables, ideal=ideal, nadir=nadir)
            elif data["problem_type"] == "Classification PIS":
                PIS = classificationPIS(
                    scalarizers=[AUG_GUESS_GLIDE, AUG_STOM_GLIDE],
                    utopian=ideal - 1e-6,
                    nadir=nadir,
                )
                # TODO: GET first preference from problem formulation!
                first_preference = {
                    "classifications": ["=", ">=", "<=", ">="],
                    "current solution": (ideal + nadir) / 2,
                    "levels": (ideal + nadir) / 2 + [0, 0.1, -0.1, 0.1],
                }
                PIS.update_preference(first_preference)
                problem = classificationPISProblem(
                    objectives=objectives,
                    variables=variables,
                    nadir=nadir,
                    ideal=ideal - 1e-6,
                    PIS=PIS,
                )
            else:
                msg = "Wrong problem type"
                return {"message": msg}, 406

            current_user = get_jwt_identity()
            current_user_id = (
                UserModel.query.filter_by(username=current_user).first().id
            )

            db.session.add(
                Problem(
                    name=data["name"],
                    problem_type=data["problem_type"],
                    problem_pickle=problem,
                    user_id=current_user_id,
                    minimize=json.dumps(minimize),
                )
            )
            db.session.commit()

            response = {
                "problem_type": data["problem_type"],
                "name": data["name"],
                "owner": current_user,
            }
            return response, 201

        elif data["problem_type"] == "Discrete":
            # handle problem with discretely defined variable-objective vector pairs, i.e., (x, f) that
            # represent a MOO problem.

            # has: problem_type, name, objectives, objective_names, variables, variable_names, ideal, nadir, minimize
            data = problem_discrete_parser.parse_args()

            # convert variables and objectives to numpy array
            try:
                xs = np.array(list(map(json.loads, data["variables"])))
                fs = np.array(list(map(json.loads, data["objectives"])))
            except Exception as e:
                print(f"DEBUG: {e}")
                message = "Could not parse given variables and/or objectives."
                return {"message": message}, 500

            # check proper length of given variable names
            if len(data["variable_names"]) != xs.shape[1]:
                message = "The number of variable names does not match the one given in the data."
                return {"message": message}, 406

            variable_names = data["variable_names"]

            # check proper length of given objective names
            if len(data["objective_names"]) != fs.shape[1]:
                message = "The number of objective names does not match the one given in the data."
                return {"message": message}, 406

            objective_names = data["objective_names"]

            # check minimize, if given
            if data["minimize"] is not None and len(data["minimize"]) != len(
                objective_names
            ):
                # minimize given, but has incorrect n of elements
                message = (
                    f"Number of elements in minimize: {data['minimize']} should match the number of elements in"
                    f"objective names: {len(objective_names)}."
                )
                return {"message": message}, 406
            elif data["minimize"] is None:
                # default value if minimize not given
                minimize = [1 for _ in objective_names]
            else:
                # minimize not None and has correct n of elements, check for correct elements, should be 1 or -1
                if not all([e in ["-1", "1"] for e in data["minimize"]]):
                    message = f"Some elements in {data['minimize']} are incorrect. Supported values are 1 and -1."
                    return {"message": message}, 406
                # correct minimize given
                minimize = list(map(int, data["minimize"]))

            # names and data given match
            # check ideal, if not given, compute from data
            if data["ideal"] is not None and len(data["ideal"]) == len(objective_names):
                # ideal of proper size given
                ideal = np.array(data["ideal"]).astype(float)
            elif data["ideal"] is not None and len(data["ideal"]) != len(
                objective_names
            ):
                # bad ideal
                message = "The dimensions of the ideal point do not match with the number of objectives."
                return {"message": message}, 406
            else:
                # ideal is None, compute it
                ideal = np.min(fs, axis=0)

            # check nadir, if not given, compute from data
            if data["nadir"] is not None and len(data["nadir"]) == len(objective_names):
                # nadir of proper size given
                nadir = np.array(data["nadir"]).astype(float)
            elif data["nadir"] is not None and len(data["nadir"]) != len(
                objective_names
            ):
                # bad nadir
                message = "The dimensions of the nadir point do not match with the number of objectives."
                return {"message": message}, 406
            else:
                # nadir is None, compute it
                nadir = np.max(fs, axis=0)

            # check that ideal and nadir make sense
            try:
                if np.any(ideal > nadir):
                    # some objective value of ideal is more than the respective one in nadir, this makes no sense
                    message = (
                        f"Given ideal and nadir are in conflict: some of the values in ideal: {ideal} are greater "
                        f"than in nadir: {nadir}."
                    )
                    return {"message": message}, 406
            except Exception as e:
                print(f"DEBUG: {e}")
                message = "Failed to compare the ideal and nadir."
                return {"message": message}, 500

            """
            response = {"problem_type": data["problem_type"], "name": data["name"], "owner": current_user}
            return response, 201
            """

            # Define dataframe
            df = pd.DataFrame(
                np.hstack((fs, xs)), columns=objective_names + variable_names
            )

            # Define problem
            problem = DiscreteDataProblem(
                df, variable_names, objective_names, ideal, nadir
            )

            # Add to DB for current user
            current_user = get_jwt_identity()
            current_user_id = (
                UserModel.query.filter_by(username=current_user).first().id
            )

            db.session.add(
                Problem(
                    name=data["name"],
                    problem_type=data["problem_type"],
                    problem_pickle=problem,
                    user_id=current_user_id,
                    minimize=json.dumps(minimize),
                )
            )
            db.session.commit()

            response = {
                "problem_type": data["problem_type"],
                "name": data["name"],
                "owner": current_user,
            }
            return response, 201
