from app import db
from desdeo_mcdm.interactive import ReferencePointMethod
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel

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
            Method(name=method_name, method_pickle=method, user_id=current_user_id, minimize=problem_minimize)
        )
        db.session.commit()

        response = {"method": method_name, "owner": current_user}

        # created
        return response, 201
