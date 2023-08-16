from flask_testing import TestCase
from flask_jwt_extended import get_jti
import json
from app import app, db
from database import db
from models.user_models import UserModel, TokenBlocklist
from desdeo_problem.testproblems import river_pollution_problem
from models.problem_models import Problem
import numpy as np
import numpy.testing as npt


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

        user_id = UserModel.query.filter_by(username="test_user").first().id

        # add river pollution problem for test_user
        problem = river_pollution_problem()
        problem.ideal = np.array([-6.34, -3.44, -7.5, 0, 0])
        problem.nadir = np.array([-4.75, -2.85, -0.32, 9.70, 0.35])
        db.session.add(
            Problem(
                name="river_pollution_problem",
                problem_type="Analytical",
                problem_pickle=problem,
                user_id=user_id,
                minimize="[1, 1, 1, 1, 1]",
            )
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

    def add_method(self, method_name, problem_name="river_pollution_problem"):
        access_token = self.login()

        # fetch problem id
        problem_id = Problem.query.filter_by(name=problem_name).first().id

        payload = json.dumps({"problem_id": problem_id, "method": method_name})

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

    def test_reference_point_method(self):
        self.add_method("reference_point_method")
        access_token = self.login()

        # start the method
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # OK
        assert response.status_code == 200

        content = json.loads(response.data)

        # iteration 1
        user_response = {"response": {
            "reference_point": [-6.34, -3.44, -7.5, 0, 0]
        }}
        payload = json.dumps(user_response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        content = json.loads(response.data)

        current_solution = content["response"]["current_solution"]
        additional_solutions = content["response"]["additional_solutions"]

        # iterations 2
        user_response = {"response": {
            "reference_point": [-4.75, -2.85, -0.32, 9.70, 0.35],
            "satisfied": False
        }}
        payload = json.dumps(user_response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        content = json.loads(response.data)

        new_current_solution = content["response"]["current_solution"]
        new_additional_solutions = content["response"]["additional_solutions"]

        with npt.assert_raises(AssertionError):
            npt.assert_almost_equal(current_solution, new_current_solution)

        with npt.assert_raises(AssertionError):
            npt.assert_almost_equal(additional_solutions, new_additional_solutions)

        # finish
        user_response = {"response": {
            "satisfied": True,
            "solution_index": 3
        }}
        payload = json.dumps(user_response)

        response = self.app.post(
            "/method/control",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 200

        content = json.loads(response.data)

        npt.assert_almost_equal(content["response"]["objective_vector"], new_additional_solutions[2])