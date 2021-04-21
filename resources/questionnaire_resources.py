from app import db
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.questionnaire_models import QuestionLikert, QuestionOpen
from models.user_models import UserModel

"""
questionnaire_get_parser = reqparse.RequestParser()
questionnaire_get_parser.add_argument(
    "questionnaire_type",
    type=str,
    help=f"The type of questionnaire to get. Available types are {available_questionnaires}",
    required=True,
)
"""


def create_likert(name: str, question_txt: str):
    return {"type": "likert", "name": name, "question_txt": question_txt, "answer": ""}


def create_differential(name: str, question_txt: str):
    return {"type": "differential", "name": name, "question_txt": question_txt, "answer": ""}


def create_open(name: str, question_txt: str):
    return {"type": "open", "name": name, "question_txt": question_txt, "answer": ""}


class QuestionnaireAfterSolutionProcess(Resource):
    @jwt_required()
    def get(self):
        questions = []

        questions.append(create_open("DP_1-1", "Why did you stop iterating?"))
        questions.append(create_likert("DP_1-4", "I am satisfied with the final solution"))
        questions.append(create_likert("LP_4-5", "I think that the solution I found is the best one"))
        questions.append(
            create_differential(
                "LP_4-2-1", "What degree of conflict do you think exists among the pair of objectives 'f1' and 'f2'?"
            )
        )
        questions.append(
            create_differential(
                "LP_4-2-2", "What degree of conflict do you think exists among the pair of objectives 'f1' and 'f3'?"
            )
        )
        questions.append(
            create_differential(
                "LP_4-2-3", "What degree of conflict do you think exists among the pair of objectives 'f2' and 'f3'?"
            )
        )
        questions.append(
            create_differential("DP_1-2-differential", "How close is the final solution to what you expected?")
        )
        questions.append(create_open("DP_1-2-open", "Please describe why?"))
        questions.append(
            create_likert(
                "LP_3-2",
                "It was easy to explore solutions with different conflicting values of the objective functions",
            )
        )
        questions.append(
            create_likert(
                "LP_4-3", "I obtained a clear idea of the possible choices available among all the possible solutions."
            )
        )
        questions.append(
            create_likert(
                "LP_4-4",
                "I obtained a clear idea of the possible choices available similar to the solutions I was interested in.",
            )
        )
        questions.append(create_open("DP_4-1", "Did some solution(s) surprise you? Why?"))
        questions.append(
            create_likert(
                "GP_2-4-likert",
                "I am satisfied with my performance (in interacting with the method) in finding my preferred solutions.",
            )
        )
        questions.append(
            create_open(
                "GP_2-4-open",
                "I am satisfied with my performance (in interacting with the method) in finding my preferred solutions.",
            )
        )
        questions.append(
            create_likert(
                "GP_2-1", "A lot of mental activity was required (e.g., thinking, deciding, and remembering)."
            )
        )
        questions.append(create_likert("GP_2-2", "Finding the preferred solution was simple."))
        questions.append(create_likert("GP_4-3", "It was easy to learn to use this method."))
        questions.append(create_likert("GP_1-2-likert", "I was able to express my preferences as I wanted."))
        questions.append(create_open("GP_1-2-open", "Please describe why?"))
        questions.append(
            create_likert(
                "LP_3-1", "In general, the method reacted to the preference information I provided as I expected."
            )
        )
        questions.append(create_likert("GP_4-1", "I felt I was in control during the solution process."))
        questions.append(create_likert("GP_4-2", "I felt comfortable using this interactive method."))
        questions.append(
            create_likert("GP_4-4", "The method has all the functions and capabilities I expected it to have.")
        )
        questions.append(
            create_likert("GP_4-5", "I was able to go backward whenever I needed in the solution process.")
        )
        questions.append(create_likert("GP_2-3", "I had to work hard to find my preferred solution."))
        questions.append(
            create_likert(
                "GP_2-5",
                "I felt frustrated in the solution process (e.g., insecure, discouraged, irritated, stressed).",
            )
        )
        questions.append(create_likert("GP_2-6", "It took too many iterations to arrive to the acceptable solution."))
        questions.append(create_likert("GP_2-7", "I felt tired."))
        questions.append(create_likert("DP_1-3-1", "Overall, I am satisfied with the ease of completing this task."))
        questions.append(
            create_likert("DP_1-3-2", "Overall, I am satisfied with the amount of time it took to complete this task.")
        )
        questions.append(
            create_likert(
                "DP_1-3-3",
                "Overall, I am satisfied with the support information (on-line help, messages, documentation) when completing this task.",
            )
        )
        questions.append(create_likert("DP_4-2-likert", "I am satisfied with the solution I chose."))
        questions.append(create_open("DP_4-2-open", "Please describe why?"))

        return {"questions": questions}, 200
