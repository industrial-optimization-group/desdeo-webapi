from app import db
from models.problem_models import Problem
from flask_jwt_extended import jwt_required, get_jwt_identity

from flask_restful import Resource, reqparse

# The vailable problem types
available_problem_types = ["Analytical"]

# Problem creation parser
problem_create_parser = reqparse.RequestParser()
problem_create_parser.add_argument(
    "problem_type",
    type=str,
    help=f"The problem type is required and must be one of {available_problem_types}",
    required=True,
)
problem_create_parser.add_argument(
    "name",
    type=str,
    help="The problem name is required",
    required=True,
)


class ProblemCreation(Resource):
    def get(self):
        return "Available problem types", 200

    @jwt_required()
    def post(self):
        data = problem_create_parser.parse_args()
        if data["problem_type"] not in available_problem_types:
            return {"message": f"The problem type must be one of {available_problem_types}"}, 406
        current_user = get_jwt_identity()
        response = {"problem_type": data["problem_type"], "name": data["name"], "owner": current_user}
        return response, 201
