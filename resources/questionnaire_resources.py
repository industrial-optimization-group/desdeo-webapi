from app import db
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.questionnaire_models import QuestionLikert, QuestionOpen
from models.user_models import UserModel

available_questionnaires = ["after_solution_process"]

questionnaire_get_parser = reqparse.RequestParser()
questionnaire_get_parser.add_argument(
    "questionnaire_type",
    type=str,
    help=f"The type of questionnaire to get. Available types are {available_questionnaires}",
    required=True,
)


class QuestionnaireGet(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        data = questionnaire_get_parser.parse_args()
        questionnaire_type = data["questionnaire_type"]

        if questionnaire_type not in available_questionnaires:
            return {"message": f"Requested questionnaire type {questionnaire_type} not found."}, 404

        # create the questions and send them
        return {"id": current_user_id}, 200
