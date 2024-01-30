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

get_utopia_map_parser = reqparse.RequestParser()

get_utopia_map_parser.add_argument(
    "problemID",
    type=int,
    help="The id of the problem these solutions are for.",
    required=True,
)

get_utopia_map_parser.add_argument(
    "solution",
    type=float,
    help="The solution to visualize.",
    required=True,
    action="append",
)

get_utopia_map_parser.add_argument(
    "Year",
    type=str,
    help="The year that should be shown on the map (as a string).",
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
        """Initialize the NIMBUS method."""
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
            user_id=current_user_id,
        )

        db.session.add(current_preference_db)
        db.session.commit()
        db.session.refresh(current_preference_db)

        # Turns out, it was a bad idea to delete previous solutions
        """
        # Remove previous solutions
        previous_saved_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        # Is this good practice? Alternatively we could just set the current solutions to saved=False
        for solution in previous_saved_solutions:
            db.session.delete(solution)
        db.session.commit()"""

        previous_saved_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
        ).all()

        solution_already_exists = False

        for solution in previous_saved_solutions:
            if np.allclose(solution.objectives, current_solution):
                solution_already_exists = True

        if not solution_already_exists:
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

        # Set previous final solutions to chosen=False
        previous_final_solutions = UTOPIASolutionArchive.query.filter_by(
            user_id=current_user_id,
            problem_id=problem_id,
            chosen=True,
        ).all()

        for solution in previous_final_solutions:
            solution.chosen = False
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
            previous_preference=initial_solution
            or ((lower_bounds + upper_bounds) / 2).tolist(),
            current_solutions=[current_solution.tolist()],
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
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
            user_id=current_user_id,
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

        # Only keep unique solutions
        current_solutions = np.unique(current_solutions, axis=0)

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
        data = choose_parser.parse_args()
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


class UtopiaMap(Resource):
    # Returns a dict with keys option and forestMap
    # option is the option for echarts
    # forestMap is a geojson for echarts.registerMap function
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        """Get the decision variables for the chosen solution."""
        data = get_utopia_map_parser.parse_args()
        problem_id = data["problemID"]
        solution = data["solution"]
        selectedYear = data["Year"]

        # Get data from the database? Get data from file? Juho can decide.
        # Check the previous post methods for how to get data from the database.

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

        problem_name = problem_query.name

        actual_problem_id = problem_name[-1]

        with open("UTOPIAdata/all_solutions.json", "r") as f:
            solutions = json.load(f)

        with open("UTOPIAdata/treatment_options.json", "r") as f:
            treatmentOptions = json.load(f)

        decision_index = "foo"
        for i in solutions[actual_problem_id]["harvest_value"]:
            if (
                solutions[actual_problem_id]["harvest_value"][i] == solution[2]
                and solutions[actual_problem_id]["npv"][i] == solution[0]
                and solutions[actual_problem_id]["stock"][i] == solution[1]
            ):
                decision_index = i

        if decision_index == "foo":
            return {"message": "Solution not found."}, 404
        
        print(solution)
        print(decision_index)

        option = {
            # // This can be used to show any picture behind the map, including an aerial image
            # /*backgroundColor: {
            #    type: 'pattern',
            #    image: 'https://upload.wikimedia.org/wikipedia/commons/b/bd/Test.svg',
            #    repeat: 'no-repeat', // You can use 'repeat-x', 'repeat-y', or 'no-repeat'
            # },*/

            "tooltip": {
                "trigger": "item",
                "showDelay": 0,
                "transitionDuration": 0.2,
                #   //borderColor: 'pink'
            },
            "visualMap": {  # // vis eg. stock levels
                "left": "right",
                #  //min: 0,
                # //max: 16,
                "showLabel": True,
                # //show: false, // put back to true when fixed the value stuff.
                # //type: 'continuous', // for stock levle
                "type": "piecewise",  # // for different plans
                # // give a map here in some manner. Make simple and start with the do nothing, cut below/top.
                "pieces": [
                    #   // Color for each plan
                    #   //{ value: 208, symbol: 'circle', label: 'do nothing', color: 'dark green' },
                    #   //{ value: 209, symbol: 'circle', label: 'above_2050', color: 'green' },
                    #   //{ value: 210, symbol: 'circle', label: 'clearcut_2040', color: 'red' },
                    #   //{ value: 231, symbol: 'circle', label: 'above 2050', color: 'green' },
                    #   //{ value: 249, symbol: 'circle', label: 'clearcut_2050', color: 'red' },
                    #   //{ value: 250, symbol: 'circle', label: 'clearcut 2040', color: 'red' },
                    #   //{ value: 251, symbol: 'circle', label: 'above_2050_', color: 'green' },
                    #   //{ value: 252, symbol: 'circle', label: "above_2040 + clearcut_2050", color: 'green' },
                    #   //{ value: 253, symbol: 'circle', label: "below_2040 + clearcut_2050", color: 'yellow' },
                    #   //{ value: 256, symbol: 'circle', label: "donothing", color: 'dark green' },
                    #   //{ value: 279, symbol: 'circle', label: "do_nothing", color: 'dark green' },
                    #   //{ value: 286, symbol: 'circle', label: "clearcut_2040_", color: 'red' },
                    #   //{ value: 11, symbol: 'rectangle', label: '123 (custom special color) ', color: 'green' },
                    #   //{ value: 2, symbol: 'diamond', label: '123 (custom special color) ', color: 'blue' },
                ],
                "text": ["Management plans"],
                # //colorBy: 'series',
                "calculable": True,
                # realtime: false
            },
            # // predefined symbols for visumap'circle': 'rect': 'roundRect': 'triangle': 'diamond': 'pin':'arrow':
            # // can give custom svgs also
            "toolbox": {
                "show": True,
                #   //orient: 'vertical',
                "left": "left",
                "top": "top",
                "feature": {
                    "dataView": {"readOnly": False},
                    "restore": {},
                    "saveAsImage": {},
                },
            },
            # // can draw graphic components to indicate different things at least
            "series": [
                {
                    "name": "Forest",
                    "type": "map",
                    "roam": True,
                    "map": "ForestMap",
                    "nameProperty": "standnumbe",
                    "colorBy": "data",
                    "itemStyle": {"symbol": "triangle", "color": "red"},
                    "data": [
                        # // The actual data is added further down.
                        # // This stuff is left here commented out to give an idea what the format should be like
                        # // Notably, using the stand IDs as values is a bad idea
                        # //{ name: "do nothing", value: 208 },
                        # //{ name: "above_2050", value: 209 },
                        # //{ name: "clearcut_2040", value: 210 },
                        # //{ name: "above 2050", value: 231 },
                        # //{ name: "clearcut_2050", value: 249 },
                        # //{ name: "clearcut 2040", value: 250 },
                        # //{ name: "above_2050_", value: 251 },
                        # //{ name: "above_2040 + clearcut_2050", value: 252 },
                        # //{ name: "below_2040 + clearcut_2050", value: 253 },
                        # //{ name: "donothing", value: 256 },
                        # //{ name: "do_nothing", value: 279 },
                        # //{ name: "clearcut_2040_", value: 286 },
                    ],
                    "nameMap": {
                        # /*208: "do nothing",
                        # 209: "above_2050",
                        # 210: "clearcut_2040",
                        # 231: "above 2050",
                        # 249: "clearcut_2050",
                        # 250: "clearcut 2040",
                        # 251: "above_2050_",
                        # 252: "above_2040 + clearcut_2050",
                        # 253: "below_2040 + clearcut_2050",
                        # 256: "donothing",
                        # 279: "do_nothing",
                        # 286: "clearcut_2040_",*/
                    },
                }
            ],
        }

        treatmentColors = {
            "nothing": "white",
            "below_2025": "yellow",
            "above_2025": "green",
            "even_2025": "blue",
            "clearcut_2025": "red",
            "first_2025": "#73b9bc",
            "below_2030": "yellow",
            "above_2030": "green",
            "even_2030": "blue",
            "clearcut_2030": "red",
            "first_2030": "#73b9bc",
            "below_2035": "yellow",
            "above_2035": "green",
            "even_2035": "blue",
            "clearcut_2035": "red",
            "first_2035": "#73b9bc",
        }
        treatmentIDs = {
            "nothing": 0,
            "below_2025": 1,
            "above_2025": 2,
            "even_2025": 3,
            "clearcut_2025": 4,
            "first_2025": 5,
            "below_2030": 1,
            "above_2030": 2,
            "even_2030": 3,
            "clearcut_2030": 4,
            "first_2030": 5,
            "below_2035": 1,
            "above_2035": 2,
            "even_2035": 3,
            "clearcut_2035": 4,
            "first_2035": 5,
        }

        dm = str(actual_problem_id)
        for stand in solutions[dm]["treatment"][decision_index]:
            option["visualMap"]["pieces"].append(
                {
                    "value": treatmentIDs[
                        treatmentOptions[
                            str(solutions[dm]["treatment"][decision_index][stand])
                        ][selectedYear]
                    ],
                    "symbol": "circle",
                    "label": treatmentOptions[
                        str(solutions[dm]["treatment"][decision_index][stand])
                    ][selectedYear],
                    "color": treatmentColors[
                        treatmentOptions[
                            str(solutions[dm]["treatment"][decision_index][stand])
                        ][selectedYear]
                    ],
                }
            )
            option["series"][0]["data"].append(
                {
                    "name": str(stand)
                    + " "
                    + treatmentOptions[
                        str(solutions[dm]["treatment"][decision_index][stand])
                    ][selectedYear],
                    "value": treatmentIDs[
                        treatmentOptions[
                            str(solutions[dm]["treatment"][decision_index][stand])
                        ][selectedYear]
                    ],
                }
            )
            option["series"][0]["nameMap"][stand] = (
                str(stand)
                + " "
                + treatmentOptions[
                    str(solutions[dm]["treatment"][decision_index][stand])
                ][selectedYear]
            )

        with open(f"UTOPIAdata/{dm}.json", "r") as f:
            forestMap = json.load(f)

        return {"option": option, "forestMap": forestMap, "mapName": "ForestMap"}, 200
