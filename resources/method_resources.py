from copy import deepcopy

import simplejson as json
from app import db
from desdeo_mcdm.interactive import NIMBUS, NautilusNavigator, NautilusNavigatorRequest, ReferencePointMethod
from desdeo_problem.problem.Problem import DiscreteDataProblem
from desdeo_emo.EAs import RVEA
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel
from utilities.expression_parser import NumpyEncoder, numpify_dict_items
import pandas as pd
import numpy as np

available_methods = {
    "reference_point_method": ReferencePointMethod,
    "reference_point_method_alt": ReferencePointMethod,  # for testing purposes only!
    "synchronous_nimbus": NIMBUS,
    "nautilus_navigator": NautilusNavigator,
    "rvea": RVEA
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
    help=(f"Specify which method to use. Available methods are: {list(available_methods.keys())}"),
    required=True,
)

method_control_parser = reqparse.RequestParser()
method_control_parser.add_argument(
    "response",
    type=dict,
    help="The response to continue iterating the method",
    required=True,
)
method_control_parser.add_argument("stop", type=bool, help="Stop and get solution?", default=False)
method_control_parser.add_argument("preference_type", type=int, help="The preference type chosen. Indexing starts at 0, -1 indicates no preference type has been chosen.", default=False)


class MethodCreate(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        method = Method.query.filter_by(user_id=current_user_id).first()
        if method is None:
            # not found
            return {"message": "No method found defined for the current user."}, 404

        # ok
        return {"message": "Method found!"}, 200

    @jwt_required()
    def post(self):
        data = method_create_parser.parse_args()

        problem_id = data["problem_id"]

        try:
            current_user = get_jwt_identity()
            current_user_id = UserModel.query.filter_by(username=current_user).first().id

            query = Problem.query.filter_by(user_id=current_user_id, id=problem_id).first()
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
        # TODO: add more methods!
        if method_name == "reference_point_method":
            method = ReferencePointMethod(problem, problem.ideal, problem.nadir)
        elif method_name == "synchronous_nimbus":
            method = NIMBUS(problem)
        elif method_name == "reference_point_method_alt":
            method = ReferencePointMethod(problem, problem.ideal, problem.nadir)
        elif method_name == "nautilus_navigator":
            if query.problem_type == "Discrete":
                problem: DiscreteDataProblem
                method = NautilusNavigator(problem.objectives, problem.ideal, problem.nadir)
            else:
                # not discrete problem
                message = "Currently NAUTILUS Navigator supports only the solving of discrete problem."
                return {"message": message}, 406
        elif method_name == "rvea":
            method = RVEA(problem, interact=True)
        else:
            # internal error
            return {"message": f"For some reason could not initialize method {method_name}"}, 500

        # add method to database, but keep only one method at any given time
        # if method already exists, delete it
        print(f"DEBUG: deleted {Method.query.filter_by(user_id=current_user_id).all()}")
        Method.query.filter_by(user_id=current_user_id).delete()
        db.session.commit()

        # add method to db
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

        response = {"method": method_name, "owner": current_user}

        # created
        return response, 201


class MethodControl(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        # check if any method has been defined
        method_query = Method.query.filter_by(user_id=current_user_id).first()

        if method_query is None:
            # not found
            return {"message": "No defined method found for the current user."}, 404

        if method_query.status != "NOT STARTED":
            # wrong method status, bad request
            return {"message": "Method has already been started."}, 400

        # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
        # TODO: use a Mutable column
        method = deepcopy(method_query.method_pickle)

        # start the method and set response
        request = method.start()
        if isinstance(request, tuple):
            # needed when multiple requests are returned as separate objects. This is needed in, e.g., NIMBUS and EA methods.
            request = request[0]

        # We dump the data here temporarily because the data must be encoded using a custom encoder to be first parsed
        # into valid JSON, then we load it again before returning.
        # ignore_nan will result in np.nan to be converted to valid null in JSON
        if isinstance(method, RVEA): # EA methods handle a bit differently, multiple requests to be handled
            contents = [json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True) for r in request]
            response = json.dumps(contents, cls=NumpyEncoder, ignore_nan=True)
        else:
            response = json.dumps(request.content, cls=NumpyEncoder, ignore_nan=True)

        # set status to iterating and last_request
        method_query.status = "ITERATING"
        method_query.last_request = request
        method_query.method_pickle = method
        db.session.commit()

        # ok
        # flask-restx will automatically parse the return value from Python dicts to valid JSON, this is why
        # we load the response in the return dict.
        if isinstance(method, RVEA):  # probably true for all EAs
            ## EA METHOD
            # Due to how EAs handle preference types, we need to also ask which
            # preference type has been selected.
            return {"response": json.loads(response), "preference_type": -1}, 200
        else:
            ## MCDM method
            # In MCDM methods, preferences are handles in a monolithic fashion (i.e., always one preference object
            # and any choices are handled IN the preference object instead of having multiple objects.)
            return {"response": json.loads(response)}, 200

    @jwt_required()
    def post(self):
        data = method_control_parser.parse_args()
        user_response_raw = data["response"]

        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        # check if any method has been defined
        method_query = Method.query.filter_by(user_id=current_user_id).first()

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

        if isinstance(method, RVEA):  # EA methods (RVEA for now) require that a preference type is chosen.
            if data["preference_type"] < 0:
                # preference type not specified
                return {
                    "message": (
                    "When using evolutionary methods, the entry in the JSON response "
                    "'preference_type' must be greater than -1."
                    )
                }, 400

        last_request = method_query.last_request

        # cast lists, which have numerical content, to numpy arrays
        user_response = numpify_dict_items(user_response_raw)

        try:
            if isinstance(method, NautilusNavigator) and user_response["go_to_previous"]:
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

            if isinstance(method, RVEA):  # and probably other EAs as well
                preference_type = data["preference_type"]
                if preference_type >= len(last_request):
                    # index out of range
                    raise IndexError(f"Index {preference_type} out of bounds.")
                else:
                    last_request = last_request[preference_type]

                if preference_type in [0, 1]:
                    # handle the preferences where a numpy array is expected
                    last_request.response = user_response["preference_data"]
                else:
                    np_preference = np.atleast_2d(user_response["preference_data"])

                    if preference_type == 2:
                        # expects pandas dataframe
                        columns = last_request.content["dimensions_data"]
                        last_request.response = pd.DataFrame(np_preference, columns=columns.columns)
                    else:
                        # preference_type 4
                        # expects numpy
                        last_request.response = np_preference
            else:
                last_request.response = user_response

            new_request = method.iterate(last_request)
            if isinstance(new_request, tuple):  # For methods that return mutliple object from an iterate call (e.g., NIMBUS (for now) and EA methods)
                new_request = new_request[0]

            method_query.method_pickle = method
            method_query.last_request = new_request
            db.session.commit()

        except Exception as e:
            print(f"DEBUG: {e}")
            # error, could not iterate, internal server error
            last_request_dump = json.dumps(last_request.content, cls=NumpyEncoder, ignore_nan=True)
            return {
                "message": "Could not iterate the method with the given response",
                "last_request": last_request_dump,
            }, 500

        # we dump the response first so that we can have it encoded into valid JSON using a custom encoder
        # ignore_nan=True will ensure np.nan is coverted to valid JSON value 'null'.
        if isinstance(method, RVEA): # EA methods handle a bit differently, multiple requests to be handled
            contents = [json.dumps(r.content, cls=NumpyEncoder, ignore_nan=True) for r in new_request]
            response = json.dumps(contents, cls=NumpyEncoder, ignore_nan=True)
        else:
            response = json.dumps(new_request.content, cls=NumpyEncoder, ignore_nan=True)

        # ok
        # We will deserialize the response into a Python dict here because flask-restx will automatically
        # serialize the response into valid JSON.
        return {"response": json.loads(response)}, 200