from copy import deepcopy

import simplejson as json
from database import db

from desdeo_emo.EAs import RVEA, NSGAIII
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from flask_restx import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem, GuestProblem
from models.user_models import (
    UserModel,
    GuestUserModel,
    role_required,
    USER_ROLE,
    GUEST_ROLE,
)
from utilities.expression_parser import NumpyEncoder, numpify_dict_items
import pandas as pd
import numpy as np
from typing import Union

available_methods = {
    "rvea": RVEA,
    "irvea": RVEA,
    "nsgaiii": NSGAIII,
    "insgaiii": NSGAIII,
}


def ea_create_parser():
    parser = reqparse.RequestParser()
    parser.add_argument(
        "problem_id",
        type=str,
        help="The id of the problem the method being created should attempt to solve.",
        required=True,
    )
    parser.add_argument(
        "method",
        type=str,
        help=(
            f"Specify which method to use. Available methods are: {list(available_methods.keys())}"
        ),
        required=True,
    )

    return parser


def ea_control_parser():
    parser = reqparse.RequestParser()
    parser.add_argument(
        "response",
        type=dict,
        help="The response to continue iterating the method",
        required=True,
    )
    parser.add_argument("stop", type=bool, help="Stop and get solution?", default=False)

    return parser


def set_interaction_type_parser():
    interaction_types = [
        "Reference point",
        "Preferred solutions",
        "Non-preferred solutions",
        "Preferred ranges",
    ]
    parser = reqparse.RequestParser()
    parser.add_argument(
        "interaction_type",
        type=str,
        help=f"The interaction type to use for the method. Available types are: {interaction_types}",
        required=True,
    )
    return parser


class EACreate(Resource):
    # TODO: Should this be extracted to a separate file to be used by other resources?
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def get(self):
        claims = get_jwt()
        current_user = get_jwt_identity()

        if claims["role"] == USER_ROLE:
            current_user_id = (
                UserModel.query.filter_by(username=current_user).first().id
            )
            method = Method.query.filter_by(user_id=current_user_id).first()
        elif claims["role"] == GUEST_ROLE:
            current_user_id = (
                GuestUserModel.query.filter_by(username=current_user).first().id
            )
            method = Method.query.filter_by(guest_id=current_user_id).first()
        else:
            return {"message": "User role not found."}, 404

        if method is None:
            # not found
            return {"message": "No method found defined for the current user."}, 404

        # ok
        return {"message": "Method found!"}, 200

    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        data = ea_create_parser(available_methods).parse_args()

        problem_id = data["problem_id"]

        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                query = Problem.query.filter_by(
                    user_id=current_user_id, id=problem_id
                ).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                query = GuestProblem.query.filter_by(
                    user_id=current_user_id, id=problem_id
                ).first()

            problem = query.problem_pickle
            problem_minimize = query.minimize

        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find problem with id={problem_id}."}, 404

        # initialize the method
        # check method is available
        method_name = data["method"]

        if method_name not in available_methods:
            # not found
            return {
                "message": (
                    f"Could not find method named {method_name}. "
                    f"Available methods are {list(available_methods.keys())}"
                )
            }, 404

        # match the method and initialize
        # TODO: add more methods here!
        if query.problem_type != "Analytical":
            # not analytical problem
            message = "Currently only analytical problems are supported."
            return {"message": message}, 406

        try:
            if method_name == "rvea":
                method = RVEA(problem, interact=False)
            elif method_name == "irvea":
                method = RVEA(problem, interact=True)
            elif method_name == "nsgaiii":
                method = NSGAIII(problem, interact=False)
            elif method_name == "insgaiii":
                method = NSGAIII(problem, interact=True)
        except Exception as e:
            print(f"DEBUG: {e}")
            # internal error
            return {
                "message": f"For some reason could not initialize method {method_name}"
            }, 500
        # add method to database, but keep only one method at any given time
        # if method already exists, delete it
        print(f"DEBUG: deleted {Method.query.filter_by(user_id=current_user_id).all()}")
        if claims["role"] == USER_ROLE:
            Method.query.filter_by(user_id=current_user_id).delete()
        elif claims["role"] == GUEST_ROLE:
            Method.query.filter_by(guest_id=current_user_id).delete()
        db.session.commit()

        # add method to db
        if claims["role"] == USER_ROLE:
            db.session.add(
                Method(
                    name=method_name,
                    method_pickle=method,
                    user_id=current_user_id,
                    minimize=problem_minimize,
                    status="NOT STARTED",
                    last_request=None,
                )
            )
            db.session.commit()
        elif claims["role"] == GUEST_ROLE:
            db.session.add(
                Method(
                    name=method_name,
                    method_pickle=method,
                    guest_id=current_user_id,
                    minimize=problem_minimize,
                    status="NOT STARTED",
                    last_request=None,
                )
            )
            db.session.commit()

        response = {"method": method_name, "owner": current_user}

        # created
        return response, 201


class EAControl(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def get(self):
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(guest_id=current_user_id).first()

        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find user with id={current_user_id}."}, 404

        if method_query is None:
            # not found
            return {"message": "No defined method found for the current user."}, 404

        if method_query.status != "NOT STARTED":
            # wrong method status, bad request
            return {"message": "Method has already been started."}, 400

        # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
        # TODO: use a Mutable column
        method = deepcopy(method_query.method_pickle)
        if (
            type(method).__name__ == RVEA.__name__
            or type(method).__name__ == NSGAIII.__name__
        ):
            return_message, request = EAControlGet(method)
        

        # set status to iterating and last_request
        method_query.status = "ITERATING"
        method_query.last_request = request
        method_query.method_pickle = method
        db.session.commit()

        return return_message

    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        data = ea_control_parser().parse_args()
        user_response_raw = data["response"]

        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(guest_id=current_user_id).first()

        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find user with id={current_user_id}."}, 404

        if method_query is None:
            # not found
            return {"message": "No defined method found for the current user."}, 404

        if method_query.status != "ITERATING":
            # wrong method status, bad request
            return {"message": "Method has not been started or is finished."}, 400

        if method_query.last_request is None:
            # method has no last request defined, bas request
            return {"message": "The method has no last request defined."}, 400

        # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
        # TODO: use a Mutable column
        method = deepcopy(method_query.method_pickle)

        if type(method).__name__ == RVEA.__name__:
            # EA methods (RVEA for now) require that a preference type is chosen.
            """if data["preference_type"] < -1:
                # preference type not specified
                return {
                    "message": (
                        "When using evolutionary methods, the entry in the JSON response "
                        "'preference_type' must be either positive, or -1 to indicate termination."
                    )
                }, 400
            elif data["preference_type"] == -1:
                # do non-dominated sorting and return
                ea_individuals, ea_objectives = method.end()
                response = json.dumps(
                    {"individuals": ea_individuals, "objectives": ea_objectives},
                    cls=NumpyEncoder,
                    ignore_nan=True,
                )
                return json.loads(response), 200"""

        last_request = method_query.last_request

        # cast lists, which have numerical content, to numpy arrays
        user_response = numpify_dict_items(user_response_raw)

        try:
            if (type(method).__name__ == NautilusNavigator.__name__) and user_response[
                "go_to_previous"
            ]:
                # for navigation methods, we need to copy the whole response as the contents of the request when going back
                # since historic information is expected in the contents, but is contained in the response.
                # TODO this is stupid, fix NautilusNavigator to expect these fields in the response instead...
                last_request = NautilusNavigatorRequest(
                    user_response["ideal"],
                    user_response["nadir"],
                    user_response["reachable_lb"],
                    user_response["reachable_ub"],
                    user_response["user_bounds"],
                    user_response["reachable_idx"],
                    user_response["step_number"],
                    user_response["steps_remaining"],
                    user_response["distance"],
                    user_response["allowed_speeds"],
                    user_response["current_speed"],
                    user_response["navigation_point"],
                )
            preference_type = data["preference_type"]

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
        if type(method).__name__ in [
            RVEA.__name__,
            IOPIS_NSGAIII.__name__,
        ]:  # EA methods handle a bit differently, multiple requests to be handled
            """contents = [
                json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True)
                for r in new_request
            ]
            response = json.dumps(contents, cls=NumpyEncoder, ignore_nan=True)"""
            ea_individuals = json.dumps(
                method.population.individuals, cls=NumpyEncoder, ignore_nan=True
            )
            ea_objectives = json.dumps(
                method.population.objectives, cls=NumpyEncoder, ignore_nan=True
            )

            ideal = json.dumps(
                method.population.problem.ideal, cls=NumpyEncoder, ignore_nan=True
            )
            nadir = json.dumps(
                method.population.problem.nadir, cls=NumpyEncoder, ignore_nan=True
            )

            # ok
            # We will deserialize the response into a Python dict here because flask-restx will automatically
            # serialize the response into valid JSON.
            return {
                "response": 0,
                "preference_type": -1,
                "individuals": json.loads(ea_individuals),
                "objectives": json.loads(ea_objectives),
                "ideal": json.loads(ideal),
                "nadir": json.loads(nadir),
            }, 200
        else:
            response = json.dumps(
                new_request.content, cls=NumpyEncoder, ignore_nan=True
            )

            # ok
            # We will deserialize the response into a Python dict here because flask-restx will automatically
            # serialize the response into valid JSON.
            return {"response": json.loads(response)}, 200


class setInteractionType(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def get(self):
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(guest_id=current_user_id).first()

        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find user with id={current_user_id}."}, 404

        if method_query is None:
            # not found
            return {"message": "No defined method found for the current user."}, 404

        method: Union[RVEA, NSGAIII] = deepcopy(method_query.method_pickle)
        return method.allowable_interaction_types, 200

    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        data = set_interaction_type_parser().parse_args()
        interaction_type = data["interaction_type"]
        # TODO: Do we really have to repeat this code everywhere?
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = (
                    UserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = (
                    GuestUserModel.query.filter_by(username=current_user).first().id
                )
                method_query = Method.query.filter_by(guest_id=current_user_id).first()

        except Exception as e:
            print(f"DEBUG: {e}")
            # not found
            return {"message": f"Could not find user with id={current_user_id}."}, 404

        if method_query is None:
            # not found
            return {"message": "No defined method found for the current user."}, 404

        if method_query.status != "ITERATING":
            # wrong method status, bad request
            return {"message": "Method has not been started or is finished."}, 400

        # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
        # TODO: use a Mutable column
        method: Union[RVEA, NSGAIII] = deepcopy(method_query.method_pickle)
        method.set_interaction_type(interaction_type)
        requests = method.requests()
        info = {}
        info["ideal"] = method.population.problem.ideal
        info["nadir"] = method.population.problem.nadir
        info["solutions"] = json.dumps(
            method.population.objectives, cls=NumpyEncoder, ignore_nan=True
        )

        method_query.method_pickle = method
        method_query.last_request = requests
        db.session.commit()

        return info, 200


def EAControlGet(method):
    method.set_interaction_type("Reference point")
    request = method.start()[0]
    """contents = [
        json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True) for r in request
    ]"""

    """response = json.dumps(contents, cls=NumpyEncoder, ignore_nan=True)"""
    ea_individuals = json.dumps(
        method.population.individuals, cls=NumpyEncoder, ignore_nan=True
    )
    ea_objectives = json.dumps(
        method.population.objectives, cls=NumpyEncoder, ignore_nan=True
    )
    # Due to how EAs handle preference types, we need to also ask which
    # preference type has been selected.
    return (
        {
            "response": 0,
            "preference_type": -1,
            "individuals": json.loads(ea_individuals),
            "objectives": json.loads(ea_objectives),
        },
        200,
    ), request


def EAControlPost(preference_type, last_request, user_response):
    # 0: No preference (get full front)
    # 1: PreferredSolutionPreference
    # 2: NonPreferredSolutionPreference
    # 3: ReferencePointPreference
    # 4: BoundPreference
    # 5: Classification

    if preference_type == 5:
        return {
            "current solution": user_response["current_solution"],
            "classifications": user_response["classifications"],
            "levels": user_response["levels"],
        }

    if preference_type > len(last_request):
        # index out of range
        # preference type not specified
        raise ValueError(f"Preference type index '{preference_type}' not valid.")
    else:
        last_request = last_request[preference_type - 1]

    if preference_type == 0:
        last_request = None

    if preference_type in [1, 2]:
        # handle the preferences where a numpy array is expected
        last_request.response = user_response["preference_data"]
    elif preference_type in [3, 4]:
        np_preference = np.atleast_2d(user_response["preference_data"])

        if preference_type == 3:
            # expects pandas dataframe
            columns = last_request.content["dimensions_data"]
            last_request.response = pd.DataFrame(np_preference, columns=columns.columns)
        else:
            # preference_type 4
            # expects numpy
            last_request.response = np_preference
    return last_request
