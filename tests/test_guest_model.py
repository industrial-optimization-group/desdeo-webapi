from flask_testing import TestCase
from flask_jwt_extended import get_jti
import json
from app import app, db
from database import db
from models.user_models import GuestUserModel
from models.method_models import Method
from resources.user_resources import default_problems

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

        data = json.loads(response.data)
        assert "access_token" in data
        assert "refresh_token" in data

        response = self.app.get("/secret", headers={"Authorization": f"Bearer {data['access_token']}"})

        # should not be able to access
        assert response.status_code == 403

        response = self.app.get("/problem/access", headers={"Authorization": f"Bearer {data['access_token']}"})
        
        # should be able to access
        assert response.status_code == 200

    def test_has_problems(self):
        response = self.app.post("/guest/create")

        # get should return 200
        assert response.status_code == 200

        data = json.loads(response.data)

        response = self.app.get("/problem/access", headers={"Authorization": f"Bearer {data['access_token']}"})
        
        # should be able to access
        assert response.status_code == 200

        data = json.loads(response.data)

        assert "problems" in data
        assert len(data["problems"]) > 0
        assert len(data["problems"]) == len(default_problems)

        for i in range(len(data["problems"])):
            assert "id" in data["problems"][i]
            assert "name" in data["problems"][i]
            assert "problem_type" in data["problems"][i]

    def test_get_all_problem_info(self):
        response = self.app.post("/guest/create")

        assert response.status_code == 200

        data = json.loads(response.data)

        response = self.app.get("/problem/access/all", headers={"Authorization": f"Bearer {data['access_token']}"})

        assert response.status_code == 200

        data = json.loads(response.data)

        assert len(data) > 1

        assert "objective_names" in data[str(1)]
        assert "variable_names" in data[str(1)]
        assert "ideal" in data[str(1)]
        assert "nadir" in data[str(1)]
        assert "n_objectives" in data[str(1)]
        assert "n_variables" in data[str(1)]
        assert "n_constraints" in data[str(1)]
        assert "minimize" in data[str(1)]
        assert "problem_name" in data[str(1)]
        assert "problem_type" in data[str(1)]
        assert "problem_id" in data[str(1)]


    def test_create_method(self):
        response = self.app.post("/guest/create")

        assert response.status_code == 200

        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "reference_point_method"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(guest_id=2).all() == [] # 2 because we set a new guest after setup

        response = self.app.post(
            "/method/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # created
        assert response.status_code == 201

        # one method should exist for the user test_user
        assert len(Method.query.filter_by(guest_id=2).all()) == 1 # 2 because we set a new guest after setup
        assert (
            Method.query.filter_by(guest_id=2).first().name == "reference_point_method"
        )

        payload = json.dumps({"problem_id": 1, "method": "reference_point_method_alt"})
        response = self.app.post(
            "/method/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # created
        assert response.status_code == 201

        # one method should still only exist
        assert len(Method.query.filter_by(guest_id=2).all()) == 1 # 2 becaseu we set a new guest after setup
        assert (
            Method.query.filter_by(guest_id=2).first().name
            == "reference_point_method_alt"
        )

    def test_method_control_get(self):
        response = self.app.post("/guest/create")

        assert response.status_code == 200

        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "reference_point_method"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(guest_id=2).all() == []

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # not found
        assert response.status_code == 404

        # create method
        response = self.app.post(
            "/method/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # created
        assert response.status_code == 201

        # check that no request is set and status is NOT STARTED
        assert len(Method.query.filter_by(guest_id=2).all()) == 1
        method_query = Method.query.filter_by(guest_id=2).first()

        assert method_query.status == "NOT STARTED"
        assert method_query.last_request is None

        # get
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # check that a request is set and status is ITERATING
        assert len(Method.query.filter_by(guest_id=2).all()) == 1
        method_query = Method.query.filter_by(guest_id=2).first()

        assert method_query.status == "ITERATING"
        assert method_query.last_request is not None

        # ok
        assert response.status_code == 200

    def test_method_control_nimbus(self):
        response = self.app.post("/guest/create")

        assert response.status_code == 200

        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 3, "method": "reference_point_method"})  # use river pollution problem (id=3)

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(guest_id=2).all() == []

        # create method
        response = self.app.post(
            "/method/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # created
        assert response.status_code == 201

        # start the method
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200


        response = {
            "response": {
                "reference_point": [-5.0, -3.0, -5.0, 5.0, 0.20],
            }
        }
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        response = {
            "response": {
                "reference_point": [-5.5, -2.8, -5.2, 5.2, 0.28],
                "satisfied": False,
            }
        }
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        response = {
            "response": {
                "reference_point": [-5.5, -2.8, -5.2, 5.2, 0.28],
                "solution_index": 1,
                "satisfied": True,
            }
        }
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200
