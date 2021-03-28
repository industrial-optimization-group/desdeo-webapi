from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel

method_create_parser = reqparse.RequestParser()
method_create_parser.add_argument(
    "problem_id",
    type=str,
    help="The id of the problem the method being created should attempt to solve.",
    required=True,
)


class MethodCreate(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        method = Method.query.filter_by(user_id=current_user_id).first()
        if method is None:
            return {"message": "No method found defined for the current user."}, 404

        return {"message": "Method found!"}, 200

    @jwt_required()
    def post(self):
        data = method_create_parser.parse_args()

        problem_id = data["problem_id"]

        try:
            current_user = get_jwt_identity()
            current_user_id = UserModel.query.filter_by(username=current_user).first().id

            problem = Problem.query.filter_by(user_id=current_user_id, id=problem_id).first().problem_pickle

        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": f"Could not find problem with id={problem_id}."}, 404

        # do something with problem
        return {"message": "ok"}, 200
