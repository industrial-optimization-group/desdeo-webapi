from copy import deepcopy
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import simplejson as json
from desdeo_mcdm.interactive.NIMBUS import (
    NIMBUS,
    NimbusClassificationRequest,
    NimbusIntermediateSolutionsRequest,
    NimbusMostPreferredRequest,
)
from desdeo_problem.problem.Problem import DiscreteDataProblem, MOProblem
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse

from database import db
from models.problem_models import GuestProblem, Problem
from models.user_models import (
    GUEST_ROLE,
    USER_ROLE,
    GuestUserModel,
    UserModel,
    role_required,
)
from utilities.expression_parser import NumpyEncoder, numpify_dict_items

initialize_parser = reqparse.RequestParser()
initialize_parser.add_argument(
    "problemId",
    type=int,
    help="The id of the problem to be solved",
    required=True,
)
initialize_parser.add_argument(
    "initialSolution",
    type=list,
    help="The initial solution or preference to be evaluated.",
    required=False,
)

iterate_parser = reqparse.RequestParser()
iterate_parser.add_argument(
    "problemId",
    type=int,
    help="The id of the problem to be solved",
    required=True,
)
iterate_parser.add_argument(
    "preference",
    type=list,
    help=(
        "The preference as a reference point. Note, NIMBUS uses classification preference,"
        " we can construct it using this reference point and the reference solution."
    ),
    required=True,
)
iterate_parser.add_argument(
    "referenceSolution",
    type=list,
    help="The reference solution to be used in the classification preference.",
    required=True,
)

intermediate_parser = reqparse.RequestParser()
intermediate_parser.add_argument(
    "problemId",
    type=int,
    help="The id of the problem to be solved",
    required=True,
)
intermediate_parser.add_argument(
    "solution1",
    type=list,
    help="The first solution for intermediate generation.",
    required=True,
)
intermediate_parser.add_argument(
    "solution2",
    type=list,
    help="The second solution for intermediate generation.",
    required=True,
)
intermediate_parser.add_argument(
    "numIntermediates",
    type=int,
    help="The number of intermediate solutions to be generated.",
    required=True,
)

save_parser = reqparse.RequestParser()
save_parser.add_argument(
    "problemId",
    type=int,
    help="The id of the problem these solutions are for.",
    required=True,
)
save_parser.add_argument(
    "solutions",
    type=list,
    help="The solutions to be saved. Maybe these are the database indices???",
    required=True,
)


class NIMBUSResponse(dataclass):
    """The response from most NIMBUS endpoints."""

    objective_names: list[str]
    is_maximized: list[bool]
    lower_bounds: list[float]
    upper_bounds: list[float]
    previousp_preference: list[float]
    current_solutions: list[list[float]]
    saved_solutions: list[list[float]]
    all_solutions: list[list[float]]


class Initialize(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        # Parsing the request
        data = initialize_parser.parse_args()
        problem_id = data["problemId"]
        initial_solution = data["initialSolution"]
        # Make sure that the initial solution is a list or None
        if initial_solution is not None or not isinstance(initial_solution, list):
            return {"message": "Initial solution must be a list or None"}, 400
        # Getting the problem from the database, annoying to extract to a function because
        # of database session issues
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                problem_query = Problem.query.filter_by(
                    id=problem_id, user_id=current_user_id
                ).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                problem_query = GuestProblem.query.filter_by(
                    id=problem_id, guest_id=current_user_id
                ).first()
        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find problem with id={problem_id}."}, 404

        if problem_query is None:
            # not found
            return {
                "message": "No problem with given ID found for the current user."
            }, 404

        problem: DiscreteDataProblem | MOProblem = problem_query.problem_pickle
        method = NIMBUS(problem, starting_point=np.array(initial_solution))
        request = method.start()

        ideal = problem.ideal
        nadir = problem.nadir
        ideal_nadir = np.vstack((ideal, nadir))
        ideal_nadir = ideal_nadir * problem._max_multiplier
        lower_bounds = np.min(ideal_nadir, axis=0)
        upper_bounds = np.max(ideal_nadir, axis=0)

        # TODO: Get the actual current solutions, saved solutions, and all solutions
        # TODO: Also, save the current solutions to the database

        response = NIMBUSResponse(
            objective_names=problem.objective_names,
            is_maximized=[
                bool(multiplier == -1) for multiplier in problem._max_multiplier
            ],
            lower_bounds=lower_bounds.tolist(),
            upper_bounds=upper_bounds.tolist(),
            previousPreference=initial_solution
            or ((lower_bounds + upper_bounds) / 2).tolist(),
            current_solutions=request.current_solutions,
            saved_solutions=request.saved_solutions,
            all_solutions=request.all_solutions,
        )
        print(response)

        return asdict(response), 200


class Iterate(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        data = iterate_parser.parse_args()
        problem_id = data["problemId"]
        preference = data["preference"]
        reference_solution = data["referenceSolution"]

        # Getting the problem from the database, annoying to extract to a function because
        # of database session issues
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                problem_query = Problem.query.filter_by(
                    id=problem_id, user_id=current_user_id
                ).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                problem_query = GuestProblem.query.filter_by(
                    id=problem_id, guest_id=current_user_id
                ).first()
        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find problem with id={problem_id}."}, 404

        if problem_query is None:
            # not found
            return {
                "message": "No problem with given ID found for the current user."
            }, 404

        problem: DiscreteDataProblem | MOProblem = problem_query.problem_pickle


        last_request = method_query.last_request

        # cast lists, which have numerical content, to numpy arrays
        user_response = numpify_dict_items(user_response_raw)

        try:
            last_request.response = user_response
            new_request = method.iterate(last_request)
            if isinstance(
                new_request, tuple
            ):  # For methods that return mutliple object from an iterate call (e.g., NIMBUS (for now) and EA methods)
                new_request = new_request[0]

            method_query.method_pickle = method
            method_query.last_request = new_request
            db.session.commit()
        except Exception as e:
            print(f"DEBUG: {e}")
            # error, could not iterate, internal server error
            if isinstance(last_request, tuple):
                last_request_dump = [
                    json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True)
                    for r in last_request
                ]
            else:
                last_request_dump = json.dumps(
                    last_request.content, cls=NumpyEncoder, ignore_nan=True
                )
            return {
                "message": "Could not iterate the method with the given response",
                "last_request": last_request_dump,
            }, 400

        # we dump the response first so that we can have it encoded into valid JSON using a custom encoder
        # ignore_nan=True will ensure np.nan is coverted to valid JSON value 'null'.

        response = json.dumps(new_request.content, cls=NumpyEncoder, ignore_nan=True)

        # ok
        # We will deserialize the response into a Python dict here because flask-restx will automatically
        # serialize the response into valid JSON.
        return {"response": json.loads(response)}, 200


class Intermediate(Resource):
    @jwt_required
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        pass


class Save(Resource):
    @jwt_required
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        pass
