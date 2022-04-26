from app import db
import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.questionnaire_models import QuestionLikert, QuestionOpen, Questionnaire
from models.user_models import UserModel
import simplejson as json

after_solution_parser = reqparse.RequestParser()
after_solution_parser.add_argument(
    "questions",
    type=dict,
    help=f"List of JSON objects with the entries 'type', 'name', 'question_txt', and 'answer'.",
    action="append",
    required=True,
)
after_solution_parser.add_argument(
    "description",
    type=str,
    help="Description of the context of the questionnaire.",
    required=True,
)


def create_likert(name: str, question_txt: str):
    return {"type": "likert", "name": name, "question_txt": question_txt, "answer": ""}


def create_differential(name: str, question_txt: str):
    return {
        "type": "differential",
        "name": name,
        "question_txt": question_txt,
        "answer": "",
    }


def create_open(name: str, question_txt: str):
    return {"type": "open", "name": name, "question_txt": question_txt, "answer": ""}


class QuestionnaireAfterSolutionProcess(Resource):
    @jwt_required()
    def get(self):
        questions = []

        questions.append(create_open("DP_1-1", "Why did you stop iterating?"))
        questions.append(
            create_likert("DP_1-4", "I am satisfied with the final solution")
        )
        questions.append(
            create_likert("LP_4-5", "I think that the solution I found is the best one")
        )
        questions.append(
            create_differential(
                "LP_4-2-1",
                "What degree of conflict do you think exists among the pair of objectives 'f1' and 'f2'?",
            )
        )
        questions.append(
            create_differential(
                "LP_4-2-2",
                "What degree of conflict do you think exists among the pair of objectives 'f1' and 'f3'?",
            )
        )
        questions.append(
            create_differential(
                "LP_4-2-3",
                "What degree of conflict do you think exists among the pair of objectives 'f2' and 'f3'?",
            )
        )
        questions.append(
            create_differential(
                "DP_1-2-differential",
                "If you imagined a desired solution in the beginning, how similar is it when compared to the final solution you obtained?",
            )
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
                "LP_4-3",
                "I obtained a clear idea of the values that the objectives (indicators) can simultaneously achieve.",
            )
        )
        questions.append(
            create_likert(
                "LP_4-4",
                "I obtained a clear idea of the possible choices available similar to the solutions I was interested in.",
            )
        )
        questions.append(
            create_open("DP_4-1", "Did some solution(s) surprise you? Why?")
        )
        questions.append(
            create_likert(
                "GP_2-4-likert",
                "I am satisfied with my performance in finding the final solution.",
            )
        )
        questions.append(
            create_open(
                "GP_2-4-open",
                "Please describe why?",
            )
        )
        questions.append(
            create_likert(
                "GP_2-1",
                "A lot of mental activity was required (e.g., thinking, deciding, and remembering).",
            )
        )
        questions.append(
            create_likert("GP_4-3", "It was easy to learn to use this method.")
        )
        questions.append(
            create_likert(
                "GP_1-2-likert",
                "I was able to reflect my actual preferences when providing the information required by the method.",
            )
        )
        questions.append(create_open("GP_1-2-open", "Please describe why?"))
        questions.append(
            create_likert(
                "LP_3-1",
                "In general, the method reacted to the preference information I provided.",
            )
        )
        questions.append(
            create_likert(
                "GP_4-1", "I felt I was in control during the solution process."
            )
        )
        questions.append(
            create_likert("GP_4-2", "I felt comfortable using this interactive method.")
        )
        questions.append(
            create_likert(
                "GP_4-4",
                "The method has all the necessary functionalities.",
            )
        )
        questions.append(
            create_likert(
                "GP_4-5",
                "I was able to return to previous solutions whenever I needed in the solution process.",
            )
        )
        questions.append(
            create_likert("GP_2-3", "I had to work hard to find the final solution.")
        )
        questions.append(
            create_likert(
                "GP_2-5",
                "I felt frustrated in the solution process (e.g., insecure, discouraged, irritated, stressed).",
            )
        )
        questions.append(
            create_likert(
                "GP_2-6",
                "It took too many iterations to arrive to the final solution.",
            )
        )
        questions.append(create_likert("GP_2-7", "I felt tired."))
        questions.append(
            create_likert(
                "DP_1-3-1",
                "Overall, I am satisfied with the ease of completing this task.",
            )
        )
        questions.append(
            create_likert(
                "DP_1-3-2",
                "Overall, I am satisfied with the amount of time it took to complete this task.",
            )
        )
        questions.append(
            create_likert(
                "DP_1-3-3",
                "Overall, I am satisfied with the support information (on-line help, messages, documentation) when completing this task.",
            )
        )
        questions.append(
            create_likert("DP_4-2-likert", "I am satisfied with the solution I chose.")
        )
        questions.append(create_open("DP_4-2-open", "Please describe why?"))
        questions.append(
            create_likert("X-1-likert", "The problem was easy to understand.")
        )
        questions.append(create_open("X-1-open", "Please describe why?"))
        questions.append(
            create_likert("X-2-likert", "The problem was important for the to solve.")
        )
        questions.append(create_open("X-2-open", "Please describe why?"))

        return {"questions": questions}, 200

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        data = after_solution_parser.parse_args()

        questions = data["questions"]
        description = data["description"]

        try:
            # create questionnaire to store answers to and add it to the DB
            questionnaire = Questionnaire(
                user_id=current_user_id,
                name="After optimization process",
                description=description,
                date=datetime.datetime.now(),
            )
            db.session.add(questionnaire)
            db.session.commit()

            # parse the answers of each question returned
            for q in questions:
                if q["type"] in ["likert", "differential"]:
                    q_to_add = QuestionLikert(
                        parent_id=questionnaire.id,
                        name=q["name"],
                        question_txt=q["question_txt"],
                        answer=q["answer"],
                    )
                    db.session.add(q_to_add)
                elif q["type"] == "open":
                    q_to_add = QuestionOpen(
                        parent_id=questionnaire.id,
                        name=q["name"],
                        question_txt=q["question_txt"],
                        answer=q["answer"],
                    )
                    db.session.add(q_to_add)
                else:
                    print(
                        f"DEBUG: while parsing questions, encountered a question of unknown type: {q['type']}"
                    )

            db.session.commit()
        except Exception as e:
            print(f"DEBUG: Got an exception while parsin questionnaire answers: {e}")
            return {"message:": "Could not parse anwers."}, 500

        return {
            "message": "Answers parsed and added to the database successfully!"
        }, 200
