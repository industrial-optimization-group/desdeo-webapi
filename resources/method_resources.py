from copy import deepcopy

import simplejson as json
from database import db
from desdeo_mcdm.interactive import (
    NIMBUS,
    NautilusNavigator,
    NautilusNavigatorRequest,
    ReferencePointMethod,
    ENautilus,
)
from desdeo_mcdm.interactive import NimbusClassificationRequest
from desdeo_problem.problem.Problem import DiscreteDataProblem
from desdeo_emo.problem import IOPISProblem
from desdeo_emo.EAs import RVEA, IOPIS_NSGAIII
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from flask_restx import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem, GuestProblem
from models.user_models import UserModel, GuestUserModel, role_required, USER_ROLE, GUEST_ROLE
from utilities.expression_parser import NumpyEncoder, numpify_dict_items
import pandas as pd
import numpy as np

available_methods = {
    "reference_point_method": ReferencePointMethod,
    "reference_point_method_alt": ReferencePointMethod,  # for testing purposes only!
    "synchronous_nimbus": NIMBUS,
    "nautilus_navigator": NautilusNavigator,
    "rvea": RVEA,
    "irvea": RVEA,
    "iopis": IOPIS_NSGAIII,
    "rvea/class": RVEA,
    "enautilus": ENautilus,
}

method_create_parser = reqparse.RequestParser()
method_create_parser.add_argument(
    "problem_id",
    type=str,
    help="The id of the problem the method being created should attempt to solve.",
    required=True,
)
method_create_parser.add_argument(
    "method",
    type=str,
    help=(
        f"Specify which method to use. Available methods are: {list(available_methods.keys())}"
    ),
    required=True,
)

method_control_parser = reqparse.RequestParser()
method_control_parser.add_argument(
    "response",
    type=dict,
    help="The response to continue iterating the method",
    required=True,
)
method_control_parser.add_argument(
    "stop", type=bool, help="Stop and get solution?", default=False
)
method_control_parser.add_argument(
    "preference_type",
    type=int,
    help="The preference type chosen. Indexing starts at 0, -1 indicates no preference type has been chosen.",
    default=None,
)


class MethodCreate(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def get(self):
        claims = get_jwt()
        current_user = get_jwt_identity()

        if claims["role"] == USER_ROLE: 
            current_user_id = UserModel.query.filter_by(username=current_user).first().id
            method = Method.query.filter_by(user_id=current_user_id).first()
        elif claims["role"] == GUEST_ROLE:
            current_user_id = GuestUserModel.query.filter_by(username=current_user).first().id
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
        data = method_create_parser.parse_args()

        problem_id = data["problem_id"]

        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE: 
                current_user_id = UserModel.query.filter_by(username=current_user).first().id
                query = Problem.query.filter_by(user_id=current_user_id, id=problem_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = GuestUserModel.query.filter_by(username=current_user).first().id
                query = GuestProblem.query.filter_by(user_id=current_user_id, id=problem_id).first()

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
        if method_name == "reference_point_method":
            method = ReferencePointMethod(problem, problem.ideal, problem.nadir)
        elif method_name == "synchronous_nimbus":
            method = NIMBUS(problem)
        elif method_name == "reference_point_method_alt":
            method = ReferencePointMethod(problem, problem.ideal, problem.nadir)
        elif method_name == "nautilus_navigator":
            if query.problem_type == "Discrete":
                problem: DiscreteDataProblem
                method = NautilusNavigator(
                    problem.objectives,
                    problem.ideal,
                    problem.nadir,
                    problem.decision_variables,
                )
                method._steps_remaining = 40
            else:
                # not discrete problem
                message = "Currently NAUTILUS Navigator supports only the solving of discrete problem."
                return {"message": message}, 406
        elif method_name == "enautilus":
            if query.problem_type == "Discrete":
                problem: DiscreteDataProblem
                method = ENautilus(
                    problem.objectives,
                    problem.ideal,
                    problem.nadir,
                    variables=problem.decision_variables,
                )
            else:
                # enautilus supports only discrete problems
                message = "E-NAUTILUS supports solcing discrete problems only"
                return {"message": message}, 406
        elif method_name == "rvea":
            if query.problem_type == "Analytical":
                method = RVEA(problem, interact=False)
            else:
                # not analytical problem
                message = "Currently RVEA supports only analytical problem types."
                return {"message": message}, 406
        elif method_name == "irvea" or method_name == "rvea/class":
            if query.problem_type == "Analytical" or "Classification PIS":
                method = RVEA(problem, interact=True)
            else:
                # not analytical problem
                message = "Currently RVEA supports only analytical problem types."
                return {"message": message}, 406
        elif method_name == "iopis":
            if query.problem_type == "Analytical":
                method = IOPIS_NSGAIII(problem)
            else:
                # not analytical problem
                message = "Currently IOPIS supports only analytical problem types."
                return {"message": message}, 406
        else:
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


class MethodControl(Resource):
    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def get(self):
        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = UserModel.query.filter_by(username=current_user).first().id
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = GuestUserModel.query.filter_by(username=current_user).first().id
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

        # EA methods handle a bit differently, multiple requests to be handled
        if type(method).__name__ == RVEA.__name__:
            return_message, request = EAControlGet(method)
        elif isinstance(method, IOPIS_NSGAIII):
            return_message, request = IOPISControlGet(method)
        else:
            # start the method and set response
            request = method.start()  # None if method is non interactive
            if isinstance(request, tuple):
                # needed when multiple requests are returned as separate objects. This is needed in, e.g., NIMBUS and EA methods.
                request = request[0]

            # We dump the data here temporarily because the data must be encoded using a custom encoder to be first parsed
            # into valid JSON, then we load it again before returning.
            # ignore_nan will result in np.nan to be converted to valid null in JSON

            response = json.dumps(request.content, cls=NumpyEncoder, ignore_nan=True)
            return_message = {"response": json.loads(response)}, 200

        # set status to iterating and last_request
        method_query.status = "ITERATING"
        method_query.last_request = request
        method_query.method_pickle = method
        db.session.commit()

        # ok
        # flask-restx will automatically parse the return value from Python dicts to valid JSON, this is why
        # we load the response in the return dict.

        ## EA METHOD
        # Due to how EAs handle preference types, we need to also ask which
        # preference type has been selected.

        ## MCDM method
        # In MCDM methods, preferences are handles in a monolithic fashion (i.e., always one preference object
        # and any choices are handled IN the preference object instead of having multiple objects.)

        return return_message

    @jwt_required()
    @role_required(USER_ROLE, GUEST_ROLE)
    def post(self):
        data = method_control_parser.parse_args()
        user_response_raw = data["response"]

        try:
            claims = get_jwt()
            current_user = get_jwt_identity()

            if claims["role"] == USER_ROLE:
                current_user_id = UserModel.query.filter_by(username=current_user).first().id
                method_query = Method.query.filter_by(user_id=current_user_id).first()
            elif claims["role"] == GUEST_ROLE:
                current_user_id = GuestUserModel.query.filter_by(username=current_user).first().id
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
            if (
                (type(method).__name__ == NautilusNavigator.__name__)
                and user_response["go_to_previous"]
            ):
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

            if type(method).__name__ == RVEA.__name__: # and probably other EAs as well
                print(user_response)
                if type(method.population.problem).__name__ == IOPISProblem.__name__:
                    if user_response["stage"] == "archive":
                        selected_solns = method.population.objectives[
                            user_response["indices"]
                        ]
                        if not hasattr(method, "archive"):
                            method.archive = selected_solns
                        else:
                            method.archive = np.vstack((method.archive, selected_solns))
                        selected_solns = json.dumps(
                            method.archive, cls=NumpyEncoder, ignore_nan=True
                        )
                        method_query.method_pickle = method
                        db.session.commit()
                        return {"response": json.loads(selected_solns)}, 200
                    if user_response["stage"] == "select":
                        selected_soln = method.archive[user_response["index"]]
                        selected_soln = json.dumps(
                            selected_soln, cls=NumpyEncoder, ignore_nan=True
                        )
                        return {"response": json.loads(selected_soln)}, 200
                last_request = EAControlPost(
                    preference_type, last_request, user_response
                )
            elif type(method).__name__ == IOPIS_NSGAIII.__name__:
                last_request = IOPISControlPost(last_request, user_response)
            else:
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
        if type(method).__name__ in [RVEA.__name__, IOPIS_NSGAIII.__name__]: # EA methods handle a bit differently, multiple requests to be handled
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


def EAControlGet(method):
    if type(method.population.problem).__name__ ==  IOPISProblem.__name__:
        method.set_interaction_type('Reference point')
        request = method.start()[0]
        """contents = [json.dumps(r, cls=NumpyEncoder, ignore_nan=True) for r in request]"""
    else:
        method.set_interaction_type('Reference point')
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


def IOPISControlGet(method):
    request = method.start()
    """contents = [
        json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True) for r in request
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
    # Due to how EAs handle preference types, we need to also ask which
    # preference type has been selected.
    return (
        {
            "response": 0,
            "preference_type": -1,
            "individuals": json.loads(ea_individuals),
            "objectives": json.loads(ea_objectives),
            "ideal": json.loads(ideal),
            "nadir": json.loads(nadir),
        },
        200,
    ), request[0]


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


def IOPISControlPost(last_request, user_response):

    np_preference = np.atleast_2d(user_response["preference_data"])
    columns = last_request.content["dimensions_data"]
    last_request.response = pd.DataFrame(np_preference, columns=columns.columns)

    return last_request
