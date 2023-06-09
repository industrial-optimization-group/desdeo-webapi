from flask_testing import TestCase
from flask_jwt_extended import get_jti
import json
from app import app, db
from database import db
from models.user_models import GuestUserModel


class TestUser(TestCase):
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

        db.session.add(GuestUserModel(username="guest_test"))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_exists(self):
        # check db for the test guest user
        guest_name = "guest_test"
        guest = GuestUserModel.query.filter_by(username=guest_name).first()

        assert guest.username == guest_name
        assert GuestUserModel.query.count() == 1

    def test_create(self):
        response = self.app.post("/guest/create")

        # get should return 200
        assert response.status_code == 200

        # check that a new guest was acutally added
        guests_n = GuestUserModel.query.count()
        assert guests_n == 2