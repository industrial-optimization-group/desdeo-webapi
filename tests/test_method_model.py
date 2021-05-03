import json

import numpy.testing as npt
from app import app, db
from desdeo_mcdm.interactive.ReferencePointMethod import ReferencePointMethod
from flask_testing import TestCase
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel


class TestMethod(TestCase):
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
            "objective_functions": ["x / y - z", "y / x - z", "z+y+x"],
            "objective_names": ["f1", "f2", "f3"],
            "variables": ["x", "y", "z"],
            "variable_initial_values": [0, 0, 0],
            "variable_bounds": [[-10, 10], [-10, 10], [-10, 10]],
            "variable_names": ["x", "y", "z"],
            "nadir": [10, 20, 30],
            "ideal": [-10, -20, -30],
            "minimize": [1, 1, 1],
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

    def testCreateModelManually(self):
        # fetch problem
        problem_pickle = Problem.query.filter_by(name="setup_test_problem_1").first()
        problem = problem_pickle.problem_pickle

        # create method and add it to the database
        objective_names = ["check", "me", "out"]
        method = ReferencePointMethod(problem, problem.ideal, problem.nadir, objective_names=objective_names)

        db.session.add(
            Method(name="ref_point_method", method_pickle=method, user_id=1, minimize=problem_pickle.minimize)
        )
        db.session.commit()

        # fetch the newly added method
        method_pickle = Method.query.filter_by(user_id=1).first()

        method_unpickle = method_pickle.method_pickle

        # check the method
        npt.assert_almost_equal(method_unpickle._problem.nadir, problem.nadir)
        npt.assert_almost_equal(method_unpickle._problem.ideal, problem.ideal)

        assert objective_names == method_unpickle._objective_names

    def testGetMethod(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        response = self.app.get(
            "/method/create",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # no method should be defined yet
        assert response.status_code == 404

    def testCreateMethod(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "reference_point_method"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(user_id=1).all() == []

        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # created
        assert response.status_code == 201

        # one method should exist for the user test_user
        assert len(Method.query.filter_by(user_id=1).all()) == 1
        assert Method.query.filter_by(user_id=1).first().name == "reference_point_method"

        payload = json.dumps({"problem_id": 1, "method": "reference_point_method_alt"})
        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # created
        assert response.status_code == 201

        # one method should still only exist
        assert len(Method.query.filter_by(user_id=1).all()) == 1
        assert Method.query.filter_by(user_id=1).first().name == "reference_point_method_alt"

    def testMethodControlGet(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "reference_point_method"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(user_id=1).all() == []

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # not found
        assert response.status_code == 404

        # create method
        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # created
        assert response.status_code == 201

        # check that no request is set and status is NOT STARTED
        assert len(Method.query.filter_by(user_id=1).all()) == 1
        method_query = Method.query.filter_by(user_id=1).first()

        assert method_query.status == "NOT STARTED"
        assert method_query.last_request is None

        # get
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # check that a request is set and status is ITERATING
        assert len(Method.query.filter_by(user_id=1).all()) == 1
        method_query = Method.query.filter_by(user_id=1).first()

        assert method_query.status == "ITERATING"
        assert method_query.last_request is not None

        # ok
        assert response.status_code == 200

    def testMethodControlRPF(self):
        return  # TODO: REMOVE ME!
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "reference_point_method"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(user_id=1).all() == []

        # create method
        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # created
        assert response.status_code == 201

        # start the method
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        method_query = Method.query.filter_by(id=1).first()
        assert method_query.method_pickle._h == 1

        # ok
        assert response.status_code == 200

        # request_content = json.loads(response.data)

        # for reference point method
        response_dict = {"response": {"reference_point": [5, -15.2, 22.2]}}
        payload = json.dumps(response_dict)

        # iterate the method
        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        method_query = Method.query.filter_by(id=1).first()
        assert method_query.method_pickle._h == 1

        # ok
        assert response.status_code == 200

        # iterate a second time
        response_dict = {"response": {"satisfied": False, "reference_point": [4, 15.2, 4.2]}}
        payload = json.dumps(response_dict)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        method_query = Method.query.filter_by(id=1).first()
        assert method_query.method_pickle._h == 2

        # ok
        assert response.status_code == 200

        # iterate a third time
        response_dict = {"response": {"satisfied": False, "reference_point": [2, 15.9, 8.2]}}
        payload = json.dumps(response_dict)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        method_query = Method.query.filter_by(id=1).first()
        assert method_query.method_pickle._h == 3

        # ok
        assert response.status_code == 200

        # stop iterating
        request_content = json.loads(json.loads(response.data)["response"])
        choice_idx = 2
        choice = request_content["additional_solutions"][choice_idx - 1]
        response_dict = {"response": {"satisfied": True, "solution_index": choice_idx}}

        payload = json.dumps(response_dict)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        method_query = Method.query.filter_by(id=1).first()
        assert method_query.method_pickle._h == 3

        request_content = json.loads(json.loads(response.data)["response"])
        final_solution = request_content["objective_vector"]
        # final_solution_x = request_content["solution"]

        npt.assert_almost_equal(final_solution, choice)

        # ok
        assert response.status_code == 200

    def testMethodControlNIMBUS(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]
        payload = json.dumps({"problem_id": 1, "method": "synchronous_nimbus"})

        # no methods should exist for the user test_user yet
        assert Method.query.filter_by(user_id=1).all() == []

        # create method
        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
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

        response = {"response": {"classifications": ["=", "0", "<"], "levels": [0, 0, 0], "number_of_solutions": 1}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": []}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": [], "number_of_desired_solutions": 0}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"index": 0, "continue": True}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {
            "response": {"classifications": ["0", "<=", ">="], "levels": [0, 8.0, -15.0], "number_of_solutions": 4}
        }
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": [0, 1, 2, 3]}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": [0, 3], "number_of_desired_solutions": 5}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": []}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        response = {"response": {"indices": [], "number_of_desired_solutions": 0}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        response = {"response": {"index": 0, "continue": False}}
        payload = json.dumps(response)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        assert response.status_code == 200

        print(json.loads(response.data))
