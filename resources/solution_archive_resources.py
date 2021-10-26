from app import db

from copy import deepcopy
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.user_models import UserModel
from models.problem_models import SolutionArchive, Problem
import simplejson as json

archive_parser = reqparse.RequestParser()
archive_parser.add_argument(
    "problem_id",
    type=int,
    help="'problem_id' is required.",
    required=True,
)
archive_parser.add_argument(
    "variables",
    type=str,
    help="'variables' missing.",
    required=True,
)
archive_parser.add_argument(
    "objectives",
    type=str,
    help="'objectives' required.",
    required=True,
)


class Archive(Resource):
    @jwt_required()
    def post(self):
        data = archive_parser.parse_args()

        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        problem_ids = [
            problem.id
            for problem in Problem.query.filter_by(user_id=current_user_id).all()
        ]

        # check that supplied problem_id exists for user
        if data["problem_id"] not in problem_ids:
            msg = f"No problem with id {data['problem_id']} exists for current user."
            return {"message": msg}, 404

        problem_id = data["problem_id"]

        # check if old solutions exists
        archive_query = SolutionArchive.query.filter_by(problem_id=problem_id).first()

        if archive_query is None:
            # add supplied solutions to new archive
            new_solutions = {
                "variables": json.loads(data["variables"]),
                "objectives": json.loads(data["objectives"]),
            }
            db.session.add(
                SolutionArchive(
                    problem_id=problem_id, solutions_dict_pickle=new_solutions
                )
            )
            db.session.commit()

            msg = f"Created new archive for problem with id {problem_id} and added solutions."
            return {"message": msg}, 201
        else:
            # add supplied solutoins to existing archive
            old_solutions = deepcopy(archive_query.solutions_dict_pickle)
            old_solutions["variables"] += json.loads(data["variables"])
            old_solutions["objectives"] += json.loads(data["objectives"])

            # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
            # TODO: use a Mutable column
            archive_query.solutions_dict_pickle = old_solutions
            db.session.commit()

            msg = (
                f"Added solutions to existing archive for problem with id f{problem_id}"
            )
            return {"message": msg}, 202