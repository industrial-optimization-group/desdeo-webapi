from flask_testing import TestCase
from flask_jwt_extended import get_jti
import json
from app import app, db
from database import db
from models.user_models import UserModel, TokenBlocklist


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

        db.session.add(UserModel(username="test_user", password=UserModel.generate_hash("pass")))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_register(self):
        response = self.app.get("/registration")

        # get should return 405
        assert response.status_code == 405

        response = self.app.post("/registration")

        # should return bad request with missing username and pasword
        assert response.status_code == 400

        payload = json.dumps({"username": "new_user", "password": "pass"})

        response = self.app.post("/registration", headers={"Content-Type": "application/json"}, data=payload)

        # new user created, OK
        assert response.status_code == 200

        # check db for new user
        new_user = UserModel.query.filter_by(username="new_user").first()

        assert new_user.username == "new_user"
        assert not new_user.username == "new_wrong_user"
        assert UserModel.verify_hash("pass", new_user.password)
        assert not UserModel.verify_hash("pass123", new_user.password)

    def test_login(self):
        response = self.app.get("/login")

        # get should return 405
        assert response.status_code == 405

        # login normal
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)

        # login ok, 200
        assert response.status_code == 200

        # check tokens exists
        data = json.loads(response.data)
        assert "access_token" in data
        assert "refresh_token" in data

        # wrong pass
        payload = json.dumps({"username": "test_user", "password": "pass123"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)

        assert response.status_code == 401

        # wrong user
        payload = json.dumps({"username": "test_user_what", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)

        assert response.status_code == 401

    def test_access_with_token(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # try access without token
        response = self.app.get("/secret")

        # unauthorized
        assert response.status_code == 401

        # try access with token
        response = self.app.get("/secret", headers={"Authorization": f"Bearer {access_token}"})

        # ok
        assert response.status_code == 200

        # check content
        assert json.loads(response.data)["answer"] == 42

        # wrong token
        response = self.app.get("/secret", headers={"Authorization": f"Bearer {refresh_token}"})

        assert response.status_code == 422

    def test_refresh_token(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # get new access token
        response = self.app.post("/token/refresh", headers={"Authorization": f"Bearer {refresh_token}"})

        # ok
        assert response.status_code == 200

        # check that access token is new
        new_access = json.loads(response.data)["access_token"]

        assert new_access != access_token

    def test_logout(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # check that current tokens not blocklisted
        assert not TokenBlocklist.query.filter_by(jti=get_jti(access_token)).first()
        assert not TokenBlocklist.query.filter_by(jti=get_jti(refresh_token)).first()

        # revoke access token
        response = self.app.post("/logout/access", headers={"Authorization": f"Bearer {access_token}"})

        # ok
        assert response.status_code == 200

        # check db
        assert get_jti(access_token) == TokenBlocklist.query.filter_by(jti=get_jti(access_token)).first().jti

        # revoke refresh token
        response = self.app.post("/logout/refresh", headers={"Authorization": f"Bearer {refresh_token}"})

        # ok
        assert response.status_code == 200

        # check db
        assert get_jti(refresh_token) == TokenBlocklist.query.filter_by(jti=get_jti(refresh_token)).first().jti
