import datetime
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Union

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
from models.method_models import Preference
from models.problem_models import GuestProblem, Problem, UTOPIASolutionArchive
from models.user_models import (
    GUEST_ROLE,
    USER_ROLE,
    GuestUserModel,
    UserModel,
    role_required,
)

initialize_parser = reqparse.RequestParser()
initialize_parser.add_argument(
    "problemID",
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
    "problemID",
    type=int,
    help="The id of the problem to be solved",
    required=True,
)
iterate_parser.add_argument(
    "preference",
    type=float,
    action="append",
    help=(
        "The preference as a reference point. Note, NIMBUS uses classification preference,"
        " we can construct it using this reference point and the reference solution."
    ),
    required=True,
)
iterate_parser.add_argument(
    "referenceSolution",
    type=float,
    action="append",
    help="The reference solution to be used in the classification preference.",
    required=True,
)

iterate_parser.add_argument(
    "numSolutions",
    type=int,
    help="The number of solutions to be generated.",
    required=True,
)

intermediate_parser = reqparse.RequestParser()
intermediate_parser.add_argument(
    "problemID",
    type=int,
    help="The id of the problem to be solved",
    required=True,
)
intermediate_parser.add_argument(
    "solution1",
    type=float,
    action="append",
    help="The first solution for intermediate generation.",
    required=True,
)
intermediate_parser.add_argument(
    "solution2",
    type=float,
    action="append",
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
    "problemID",
    type=int,
    help="The id of the problem these solutions are for.",
    required=True,
)


save_parser.add_argument(
    "previousPreference",
    type=float,
    action="append",
    help="The previous preference.",
    required=True,
)

save_parser.add_argument(
    "objectiveValues",
    type=list,
    help="The solutions to be saved. Maybe these are the database indices???",
    required=True,
    location="json",
)

choose_parser = reqparse.RequestParser()

choose_parser.add_argument(
    "problemID",
    type=int,
    help="The id of the problem these solutions are for.",
    required=True,
)

choose_parser.add_argument(
    "solution",
    type=float,
    help="The solution to be saved. Maybe these are the database indices???",
    required=True,
    action="append",
)

get_decision_variables_parser = reqparse.RequestParser()

get_decision_variables_parser.add_argument(
    "problemID",
    type=int,
    help="The id of the problem these solutions are for.",
    required=True,
)

get_decision_variables_parser.add_argument(
    "UserName",
    type=str,
    help="The username of the user.",
    required=True,
)


@dataclass
class NIMBUSResponse:
    """The response from most NIMBUS endpoints."""

    objective_names: list[str]
    is_maximized: list[bool]
    lower_bounds: list[float]
    upper_bounds: list[float]
    previous_preference: list[float]
    current_solutions: list[list[float]]
    saved_solutions: list[list[float]]
    all_solutions: list[list[float]]


class Initialize(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Initialize the NIMBUS method.
        """
        # Parsing the request
        data = initialize_parser.parse_args()
        initial_solution = data["initialSolution"]
        problem_id = data["problemID"]
        # Make sure that the initial solution is a list or None
        if initial_solution is not None and not isinstance(initial_solution, list):
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

        problem: Union[DiscreteDataProblem, MOProblem] = problem_query.problem_pickle

        ideal = problem.ideal
        nadir = problem.nadir
        max_multiplier = np.array(json.loads(problem_query.minimize), dtype=int)
        print(ideal)
        print(nadir)

        ideal_nadir = np.vstack((ideal, nadir))
        ideal_nadir = ideal_nadir * max_multiplier
        lower_bounds = np.min(ideal_nadir, axis=0)
        upper_bounds = np.max(ideal_nadir, axis=0)
        if initial_solution is not None:
            initial_solution = np.array(initial_solution, dtype=float) * max_multiplier

        method = NIMBUS(problem, starting_point=initial_solution)
        request = method.start()
        current_solution = request[0].content["objective_values"] * max_multiplier

        preference = (ideal + nadir) / 2
        preference = preference * max_multiplier

        current_preference_db = Preference(
            method="NIMBUS",
            preference={"initial preference": preference.tolist()},
            date=datetime.datetime.now(),
        )

        db.session.add(current_preference_db)
        db.session.commit()
        db.session.refresh(current_preference_db)

        # Remove previous solutions
        previous_saved_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        # Is this good practice? Alternatively we could just set the current solutions to saved=False
        for solution in previous_saved_solutions:
            db.session.delete(solution)
        db.session.commit()

        db.session.add(
            UTOPIASolutionArchive(
                user_id=current_user_id,
                problem_id=problem_id,
                preference=current_preference_db.id,
                method_name="NIMBUS",
                objectives=current_solution.tolist(),
                variables=[],  # Don't have access to these yet
                date=datetime.datetime.now(),
                saved=True,
                current=True,
                chosen=False,
            )
        )
        db.session.commit()

        response = NIMBUSResponse(
            objective_names=problem.objective_names,
            is_maximized=[bool(multiplier == -1) for multiplier in max_multiplier],
            lower_bounds=lower_bounds.tolist(),
            upper_bounds=upper_bounds.tolist(),
            previous_preference=initial_solution
            or ((lower_bounds + upper_bounds) / 2).tolist(),
            current_solutions=[current_solution.tolist()],
            saved_solutions=[current_solution.tolist()],
            all_solutions=[current_solution.tolist()],
        )

        return asdict(response), 200


class Iterate(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Iterate the NIMBUS method."""
        data = iterate_parser.parse_args()
        problem_id = data["problemID"]
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

        problem: Union[DiscreteDataProblem, MOProblem] = problem_query.problem_pickle
        max_multiplier = np.array(json.loads(problem_query.minimize), dtype=int)
        ideal = problem.ideal
        nadir = problem.nadir

        ideal_nadir = np.vstack((ideal, nadir))
        ideal_nadir = ideal_nadir * max_multiplier
        lower_bounds = np.min(ideal_nadir, axis=0)
        upper_bounds = np.max(ideal_nadir, axis=0)

        preference = np.array(preference, dtype=float) * max_multiplier
        reference_solution = np.array(reference_solution, dtype=float) * max_multiplier

        # Check if classification preference is valid.
        # At least one element of preference must be less than or equal to reference solution
        # and at least one element of preference must be greater than or equal to reference solution.
        pref_less = np.less_equal(preference, reference_solution)
        pref_greater = np.greater_equal(preference, reference_solution)

        if not np.any(pref_less) or not np.any(pref_greater):
            return {
                "message": (
                    "The preference must be valid classification preference."
                    " At least one element of preference must be less than or equal to reference solution"
                    " and at least one element of preference must be greater than or equal to reference solution."
                )
            }, 400

        method = NIMBUS(problem, starting_point=reference_solution)
        request: NimbusClassificationRequest = method.start()[0]

        classes = [None for _ in range(len(preference))]
        levels = [None for _ in range(len(preference))]

        for i, (pref, ref) in enumerate(zip(preference, reference_solution)):
            if pref == ideal[i]:
                classes[i] = "<"
                levels[i] = ideal[i]
            elif pref == nadir[i]:
                classes[i] = "0"
                levels[i] = nadir[i]
            elif pref == ref:
                classes[i] = "="
                levels[i] = ref[i]
            elif pref < ref:
                classes[i] = "<="
                levels[i] = pref
            elif pref > ref:
                classes[i] = ">="
                levels[i] = pref
            else:
                return {"message": "Something went wrong with the classification."}, 400
        response = {
            "classifications": classes,
            "number_of_solutions": data["numSolutions"],
            "levels": np.array(levels),
        }
        request.response = response

        request = method.iterate(request)[0]
        current_solutions = request.content["objectives"] * max_multiplier

        response["levels"] = response["levels"].tolist()

        current_preference_db = Preference(
            method="NIMBUS",
            preference={"classification preference": response},
            date=datetime.datetime.now(),
        )
        db.session.add(current_preference_db)
        db.session.commit()
        db.session.refresh(current_preference_db)

        # Set previous current solutions to saved=False
        previous_current_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            current=True,
        ).all()
        for solution in previous_current_solutions:
            solution.current = False
        db.session.commit()

        for solution in current_solutions:
            db.session.add(
                UTOPIASolutionArchive(
                    user_id=current_user_id,
                    problem_id=problem_id,
                    preference=current_preference_db.id,
                    method_name="NIMBUS",
                    objectives=solution.tolist(),
                    variables=[],  # Don't have access to these yet
                    date=datetime.datetime.now(),
                    saved=False,
                    current=True,
                    chosen=False,
                )
            )
            db.session.commit()

        saved_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            saved=True,
        ).all()

        saved_solutions = [solution.objectives for solution in saved_solutions]

        all_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        all_solutions = [solution.objectives for solution in all_solutions]

        response = NIMBUSResponse(
            objective_names=problem.objective_names,
            is_maximized=[bool(multiplier == -1) for multiplier in max_multiplier],
            lower_bounds=lower_bounds.tolist(),
            upper_bounds=upper_bounds.tolist(),
            previous_preference=(response["levels"] * max_multiplier).tolist(),
            current_solutions=current_solutions.tolist(),
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
        )
        print(response)
        # Temporary return to satisfy linter
        return asdict(response), 200


class Intermediate(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Generate intermediate solutions. Doesn't work yet."""
        pass


class Save(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Save or highlight solutions."""
        # Parsing the request
        data = save_parser.parse_args()
        problem_id = data["problemID"]
        objective_values = data["objectiveValues"]

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

        problem: Union[DiscreteDataProblem, MOProblem] = problem_query.problem_pickle
        ideal = problem.ideal
        nadir = problem.nadir
        max_multiplier = np.array(json.loads(problem_query.minimize), dtype=int)

        ideal_nadir = np.vstack((ideal, nadir))
        ideal_nadir = ideal_nadir * max_multiplier
        lower_bounds = np.min(ideal_nadir, axis=0)
        upper_bounds = np.max(ideal_nadir, axis=0)
        # Get solutions from database
        solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            saved=False,
        ).all()

        for obj_vector in objective_values:
            for solution in solutions:
                if np.allclose(solution.objectives, obj_vector):
                    solution.saved = True
                    print(f"Saved solution {solution.id}")

        db.session.commit()

        saved_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            saved=True,
        ).all()

        all_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        current_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            current=True,
        ).all()

        response = NIMBUSResponse(
            objective_names=problem.objective_names,
            is_maximized=[bool(multiplier == -1) for multiplier in max_multiplier],
            lower_bounds=lower_bounds.tolist(),
            upper_bounds=upper_bounds.tolist(),
            previous_preference=data["previousPreference"],
            current_solutions=[solution.objectives for solution in current_solutions],
            saved_solutions=[solution.objectives for solution in saved_solutions],
            all_solutions=[solution.objectives for solution in all_solutions],
        )

        return asdict(response), 200


class Choose(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Choose a solution as the final solution."""
        # Parsing the request
        data = save_parser.parse_args()
        problem_id = data["problemID"]
        chosen_solution = data["solution"]

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

        # Ensure that no other solution is chosen
        chosen_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            chosen=True,
        ).all()

        if len(chosen_solutions) > 0:
            return {"message": "Another solution has already been chosen."}, 400

        # Get solutions from database
        solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        for solution in solutions:
            if np.allclose(solution.objectives, chosen_solution):
                solution.chosen = True
                print(f"Chosen solution {solution.id}")

        db.session.commit()

        chosen_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            chosen=True,
        ).all()

        return {"message": "Solution chosen."}, 200


class GetDecisionVariables(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Get the decision variables for the chosen solution."""
        data = choose_parser.parse_args()
        problem_id = data["problemID"]
        user_name = data["UserName"]

        # Get data from the database? Get data from file? Juho can decide.
        # Check the previous post methods for how to get data from the database.

        pass
