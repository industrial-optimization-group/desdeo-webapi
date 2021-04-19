import datetime

from app import app, db
from flask_testing import TestCase
from models.questionnaire_models import QuestionLikert, Questionnaire, QuestionOpen
from models.user_models import UserModel


class TestQuestionnaire(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    TESTING = True

    def create_app(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = self.SQLALCHEMY_DATABASE_URI
        app.config["TESTING"] = self.TESTING
        return app

    def setUp(self):
        db.create_all()
        self.app = app.test_client()

        db.session.add(UserModel(username="test_user", password=UserModel.generate_hash("pass")))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_save_questionnaire(self):
        user_id = UserModel.query.filter_by(username="test_user").first().id

        # create questionnaire
        questionnaire = Questionnaire(user_id=user_id, name="test questionnaire", date=datetime.datetime.now())
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
