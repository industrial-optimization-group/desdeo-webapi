import json

import numpy as np
import numpy.testing as npt
from app import app, db
from flask_testing import TestCase
from models.problem_models import Problem
from models.user_models import UserModel


class TestProblem(TestCase):
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
        db.session.add(UserModel(username="sad_user", password=UserModel.generate_hash("pass")))
        db.session.commit()

        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        problem_def = {
            "problem_type": "Analytical",
            "name": "setup_test_problem_1",
            "objective_functions": ["x+y", "x-z", "z+y+x"],
            "objective_names": ["f1", "f2", "f3"],
            "variables": ["x", "y", "z"],
            "variable_initial_values": [0, 0, 0],
            "variable_bounds": [[-10, 10], [-10, 10], [-10, 10]],
            "variable_names": ["x", "y", "z"],
            "ideal": [10, 20, 30],
            "nadir": [-10, -20, -30],
            "minimize": [1, -1, 1],
        }

        payload = json.dumps(problem_def)
        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        problem_def["name"] = "setup_test_problem_2"
        payload = json.dumps(problem_def)
        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        problem_def["name"] = "setup_test_problem_3"
        payload = json.dumps(problem_def)
        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 201

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_access_problem(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        response = self.app.get(
            "/problem/access",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # ok
        assert response.status_code == 200

        data = json.loads(response.data)

        # the three problems defined in set_up
        assert len(data["problems"]) == 3

        payload = json.dumps({"username": "sad_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        response = self.app.get(
            "/problem/access",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # ok
        assert response.status_code == 200

        data = json.loads(response.data)

        # no problems defined in set_up for sad user!
        assert len(data["problems"]) == 0

    def test_get_problem(self):
        response = self.app.get("/problem/create")

        # unauthorized
        assert response.status_code == 401

        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)

        assert response.status_code == 200

        data = json.loads(response.data)
        response = self.app.get(
            "/problem/create",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )

        data = json.loads(response.data)

        assert data["available_problem_types"] is not None

    def test_create_analytical_problem(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        payload = json.dumps(
            {
                "problem_type": "Analytical",
                "name": "analytical_test_problem",
            }
        )

        # Missing objective functions
        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # 400
        assert response.status_code == 400

        # Missing variable bounds
        # three objective functions given
        obj_fun_1 = "2*x-y"
        obj_fun_2 = "x+2*y/z"
        obj_fun_3 = "x+y+z+x"
        objectives = [obj_fun_1, obj_fun_2, obj_fun_3]

        variables = ["x", "y", "z"]

        payload = json.dumps(
            {
                "problem_type": "Analytical",
                "name": "analytical_test_problem",
                "objective_functions": objectives,
                "variables": variables,
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # 406
        assert response.status_code == 400

        variable_bounds = [[-5, 5], [-15, 15], [-20, 20]]
        initial_values = [5, 2, 3]
        variable_names = ["speed", "luck", "dex"]

        objective_names = ["profit", "loss", "impact"]

        ideal = [10, 20, 30]
        nadir = [-10, -20, -30]

        minimize = [1, -1, 1]

        payload = json.dumps(
            {
                "problem_type": "Analytical",
                "name": "analytical_test_problem",
                "objective_functions": objectives,
                "objective_names": objective_names,
                "variables": variables,
                "variable_initial_values": initial_values,
                "variable_bounds": variable_bounds,
                "variable_names": variable_names,
                "ideal": ideal,
                "nadir": nadir,
                "minimize": minimize,
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 201

        # fetch problem and check it
        problem = Problem.query.filter_by(name="analytical_test_problem").first()

        assert problem.name == "analytical_test_problem"

        user_id = UserModel.query.filter_by(username="test_user").first().id
        assert problem.user_id == user_id
        assert problem.problem_type == "Analytical"
        npt.assert_almost_equal(json.loads(problem.minimize), minimize)

        unpickled = problem.problem_pickle

        assert unpickled.get_variable_names() == variable_names
        assert unpickled.get_objective_names() == objective_names

        assert unpickled.variables[0].current_value == 5
        assert unpickled.variables[1].current_value == 2
        assert unpickled.variables[2].current_value == 3

        assert unpickled.variables[0].get_bounds() == (-5, 5)
        assert unpickled.variables[1].get_bounds() == (-15, 15)
        assert unpickled.variables[2].get_bounds() == (-20, 20)

        npt.assert_almost_equal(unpickled.ideal, ideal)
        npt.assert_almost_equal(unpickled.nadir, nadir)

        res = unpickled.evaluate(np.array([[2, 1, 3], [3, 2, 1]])).objectives

        npt.assert_almost_equal(res[0], np.array([3, 2.66666666, 8]))
        npt.assert_almost_equal(res[1], np.array([4, 7, 9]))
