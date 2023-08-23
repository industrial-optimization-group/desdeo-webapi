import datetime
import pytest
import json

from app import app
from database import db
from flask_testing import TestCase
from models.questionnaire_models import QuestionLikert, Questionnaire, QuestionOpen
from models.user_models import UserModel


@pytest.mark.questionnaire
class TestQuestionnaire(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    TESTING = True

    def create_app(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = self.SQLALCHEMY_DATABASE_URI
        app.config["TESTING"] = self.TESTING
        return app

    def setUp(self):
        db.drop_all()
        db.create_all()
        self.app = app.test_client()

        db.session.add(
            UserModel(username="test_user", password=UserModel.generate_hash("pass"))
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, uname="test_user", pword="pass"):
        # login and get access token for test user
        payload = json.dumps({"username": uname, "password": pword})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
        data = json.loads(response.data)

        access_token = data["access_token"]

        return access_token

    def test_save_questionnaire(self):
        user_id = UserModel.query.filter_by(username="test_user").first().id

        # create questionnaire
        questionnaire = Questionnaire(
            user_id=user_id,
            name="test questionnaire",
            start_time=datetime.datetime.now(),
            completion_time=datetime.datetime.now(),
            description="Testing",
        )
        db.session.add(questionnaire)
        db.session.commit()

        # create some example questions

        likert_1 = QuestionLikert(
            parent_id=questionnaire.id,
            name="likert_1",
            question_txt="This is an example question that expects an answer, which lies on the Likert scale",
            answer=1,
        )
        db.session.add(likert_1)

        likert_2 = QuestionLikert(
            parent_id=questionnaire.id,
            name="likert_2",
            question_txt="This is an example question that expects an answer, which lies on the Likert scale",
            answer=7,
        )
        db.session.add(likert_2)

        likert_3 = QuestionLikert(
            parent_id=questionnaire.id,
            name="likert_3",
            question_txt="This is an example question that expects an answer, which lies on the Likert scale",
            answer=4,
        )
        db.session.add(likert_3)

        open_1 = QuestionOpen(
            parent_id=questionnaire.id,
            name="open_1",
            question_txt="This is an example question that expects an open-ended answer",
            answer="This is an open ended answer.",
        )
        db.session.add(open_1)

        open_2 = QuestionOpen(
            parent_id=questionnaire.id,
            name="open_1",
            question_txt="This is an example question that expects an open-ended answer",
            answer="This is an open ended answer.",
        )
        db.session.add(open_2)

        db.session.commit()

        # check for correct number of children
        assert len(questionnaire.questions_likert) == 3
        assert len(questionnaire.questions_open) == 2

    def test_get_questionnaire_after(self):
        access_token = self.login()

        response = self.app.get(
            "/questionnaire/after",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "start_time" in data

        assert len(data["questions"]) == 36

    def test_post_questionnaire_after(self):
        access_token = self.login()

        # get questions
        response = self.app.get(
            "/questionnaire/after",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "questions" in data
        assert "start_time" in data

        # give dummy answers to each question depending on type
        questions = data["questions"]
        for i, q in enumerate(questions):
            if q["type"] == "likert":
                answer = 3
            elif q["type"] == "differential":
                answer = 2
            elif q["type"] == "open":
                answer = "test response"
            else:
                assert False

            q["answer"] = answer

            questions[i] = q

        description = "Test description"
        payload = json.dumps(
            {
                "questions": questions,
                "description": description,
                "start_time": data["start_time"],
            }
        )

        response = self.app.post(
            "/questionnaire/after",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        # check that the questions saved to the DB have the correct answers
        user_id = UserModel.query.filter_by(username="test_user").first().id

        questionnaire = Questionnaire.query.filter_by(user_id=user_id).first()

        # check likert and differential questions
        for ql in questionnaire.questions_likert:
            assert ql.answer in [2, 3]

        # check open questions
        for qo in questionnaire.questions_open:
            assert qo.answer == "test response"

        # check that all questions are present
        assert (
            len(questionnaire.questions_likert) + len(questionnaire.questions_open)
            == 36
        )

        # check that start time is less than completion time
        assert questionnaire.start_time < questionnaire.completion_time

        # check the description is correct
        assert questionnaire.description == "Test description"

    def test_get_questionnaire_during(self):
        access_token = self.login()

        response = self.app.get(
            "/questionnaire/during",
            headers={
                "Authorization": f"Bearer {access_token}",
            }
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["questions"]) == 1
        assert "start_time" in data

        # check the questions
        assert data["questions"][0]["name"] == "GP_1-3"

    def test_get_questionnaire_during_first(self):
        access_token = self.login()

        response = self.app.get(
            "/questionnaire/during/first",
            headers={
                "Authorization": f"Bearer {access_token}",
            }
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["questions"]) == 2
        assert "start_time" in data

        # check the questions
        assert data["questions"][0]["name"] == "GP_1-1"
        assert data["questions"][1]["name"] == "GP_1-3"

    def test_get_questionnaire_during_after_new(self):
        access_token = self.login()

        response = self.app.get(
            "/questionnaire/during/new",
            headers={
                "Authorization": f"Bearer {access_token}",
            }
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["questions"]) == 2
        assert "start_time" in data

        # check the questions
        assert data["questions"][0]["name"] == "LP_3-3"
        assert data["questions"][1]["name"] == "LP_4-1"

    def test_post_questionnaire(self):
        access_token = self.login()

        # first iteration
        iteration = 1
        payload = json.dumps({"iteration": iteration})

        response = self.app.get(
            "/questionnaire/during/first",
            headers={
                "Authorization": f"Bearer {access_token}",
            }
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["questions"]) == 2
        assert "start_time" in data

        # answer the questions
        questions = data["questions"]

        questions[0]["answer"] = 5
        questions[1]["answer"] = "A nice solution."

        description = "Testing"
        payload = json.dumps(
            {
                "iteration": iteration,
                "questions": questions,
                "description": description,
                "start_time": data["start_time"],
            }
        )

        response = self.app.post(
            "/questionnaire/during",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        # check that the questions saved to the DB have the correct answers
        user_id = UserModel.query.filter_by(username="test_user").first().id

        questionnaire = Questionnaire.query.filter_by(user_id=user_id).first()

        # check likert and differential questions
        for ql in questionnaire.questions_likert:
            assert ql.answer in [5]

        # check open questions
        for qo in questionnaire.questions_open:
            assert qo.answer == "A nice solution."

        # check start_time is less than completion_time
        assert questionnaire.start_time < questionnaire.completion_time