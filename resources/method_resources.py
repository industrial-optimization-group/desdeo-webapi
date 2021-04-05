import json
from copy import deepcopy

from app import db
from desdeo_mcdm.interactive import ReferencePointMethod
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel
from utilities.expression_parser import NumpyEncoder, numpify_dict_items

available_methods = {
    "reference_point_method": ReferencePointMethod,
    "reference_point_method_alt": ReferencePointMethod,  # for testing purposes only!
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

            problem_match = Problem.query.filter_by(user_id=current_user_id, id=problem_id).first()
            problem = problem_match.problem_pickle
            problem_minimize = problem_match.minimize

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
        elif method_name == "reference_point_method_alt":
            method = ReferencePointMethod(problem, problem.ideal, problem.nadir)
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
        response = json.dumps(request.content, cls=NumpyEncoder)

        # set status to iterating and last_request
        method_query.status = "ITERATING"
        method_query.last_request = request
        method_query.method_pickle = method
        db.session.commit()

        # ok
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
        last_request = method_query.last_request

        # cast lists, which have numerical content, to numpy arrays
        user_response = numpify_dict_items(user_response_raw)

        last_request.response = user_response

        try:
            # attempt to iterate and update method and last_request pickles
            new_request = method.iterate(last_request)
            method_query.method_pickle = method
            method_query.last_request = new_request
            db.session.commit()
        except Exception as e:
            print(f"DEBUG: {e}")
            # error, could not iterate, internal server error
            last_request_dump = json.dumps(last_request.content, cls=NumpyEncoder)
            return {
                "message": "Could not iterate the method with the given response",
                "last_request": last_request_dump,
            }, 500

        response = json.dumps(new_request.content, cls=NumpyEncoder)

        # ok
        return {"response": response}, 200
