import os

import numpy as np
import numpy.testing as npt
import pytest
import simplejson as json
from app import app, db
from desdeo_problem.testproblems import test_problem_builder as problem_builder
from desdeo_emo.EAs import RVEA
from desdeo_tools.interaction import BoundPreference, NonPreferredSolutionPreference, PreferredSolutionPreference, ReferencePointPreference
from flask_testing import TestCase
from models.method_models import Method
from models.problem_models import Problem
from models.user_models import UserModel


@pytest.mark.method
@pytest.mark.emo
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
        db.session.commit()

        user_id = UserModel.query.filter_by(username="test_user").first().id

        # add DTLZ2 for test_user
        problem = problem_builder("DTLZ2", n_of_variables=5, n_of_objectives=4)
        db.session.add(Problem(name="DTLZ2", problem_type="Analytical", problem_pickle=problem, user_id=user_id, minimize="[1, 1, 1, 1]"))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, uname="test_user", pword="pass"):
        # login and get access token for test user
        payload = json.dumps({"username": uname, "password": pword})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        return access_token

    def add_method(self):
        access_token = self.login()

        # fetch problem id
        problem_id = Problem.query.filter_by(name="DTLZ2").first().id 

        payload = json.dumps({"problem_id": problem_id, "method": "rvea"})

        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            data=payload,
        )

        # created
        assert response.status_code == 201

    def testCreateRVEA(self):
        """ Test that RVEA is properly created and added to the database via an HTTP call.
        """
        self.add_method()

        # fetch user id
        user_id = UserModel.query.filter_by(username="test_user").first().id

        # check method properly in DB
        method = Method.query.filter_by(user_id=user_id).first().method_pickle

        assert isinstance(method, RVEA)

        # check it is interactive
        assert method.interact  # True

        # check the status of the method is proper
        method_status = Method.query.filter_by(user_id=user_id).first().status

        assert method_status == "NOT STARTED"

    def testStartRVEA(self):
        access_token = self.login()
        self.add_method()

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Ok
        assert response.status_code == 200

        data = json.loads(response.data)

        # Check that all possible responses are present
        assert len(data["response"]) == 4

        # Check that each response contains a 'message' entry
        assert all(["message" in r for r in data["response"]])

        # Check method status in DB
        method_q = Method.query.filter_by(id=1).first()
        method_status = method_q.status

        assert method_status == "ITERATING"

        # Check the status types in the database method object
        last_request = method_q.last_request

        assert isinstance(last_request[0], PreferredSolutionPreference)
        assert isinstance(last_request[1], NonPreferredSolutionPreference)
        assert isinstance(last_request[2], ReferencePointPreference)
        assert isinstance(last_request[3], BoundPreference)
        
"""
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


@pytest.mark.nautilusnav
@pytest.mark.method
class TestNautilusNavigator(TestCase):
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

        atoken = self.login()

        xs, fs = self.get_xs_and_fs()

        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11"],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
            data=payload,
        )

        if response.status_code != 201:
            # ABORT, failed to add problem to DB!
            self.tearDown()
            pytest.exit(f"FATAL ERROR: Could not add problem during setup in {__file__}.")
            exit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, uname="test_user", pword="pass"):
        # login and get access token for test user
        payload = json.dumps({"username": uname, "password": pword})
        response = self.app.post("/login", headers={"Content-Type": "application/json"}, data=payload)
        data = json.loads(response.data)

        access_token = data["access_token"]

        return access_token

    def get_xs_and_fs(self, path=os.path.dirname(os.path.abspath(__file__)), fname="data/testPF_3f_11x_max.csv"):
        pf = np.loadtxt(f"{path}/{fname}", delimiter=",")
        fs = list(map(list, -pf[:, 0:3]))
        xs = list(map(list, pf[:, 3:]))

        # the minus because the problem has been specified to be maximized in testPF_3f_11x_max.csv
        return xs, fs

    def test_create_method(self):
        uname = "test_user"
        atoken = self.login(uname=uname)
        method_name = "nautilus_navigator"

        # create a nautilus navigator method
        response = self.app.get(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
        )

        # no method created for user
        assert response.status_code == 404

        # create method
        payload = json.dumps({"problem_id": 1, "method": method_name})

        response = self.app.post(
            "/method/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
            data=payload,
        )

        data = json.loads(response.data)

        assert data["method"] == method_name
        assert data["owner"] == uname

        # created
        assert response.status_code == 201

    def test_start_method(self):
        uname = "test_user"
        atoken = self.login(uname=uname)

        self.test_create_method()

        # start method
        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {atoken}"},
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "response" in data
        assert "message" in data["response"]
        assert "ideal" in data["response"]
        assert "nadir" in data["response"]
        assert "reachable_lb" in data["response"]
        assert "reachable_ub" in data["response"]
        assert "user_bounds" in data["response"]
        assert "reachable_idx" in data["response"]
        assert "step_number" in data["response"]
        assert "steps_remaining" in data["response"]
        assert "distance" in data["response"]
        assert "allowed_speeds" in data["response"]
        assert "current_speed" in data["response"]
        assert "navigation_point" in data["response"]

    def test_iterate_method(self):
        uname = "test_user"
        atoken = self.login(uname=uname)

        self.test_create_method()

        # start method
        response = self.app.get(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
        )

        assert response.status_code == 200

        content = json.loads((response.data))["response"]

        # first iteration
        assert content["step_number"] == 1

        # iterate method once
        lower_b = content["reachable_lb"]
        upper_b = content["reachable_ub"]

        # set ref_point as middle of bounds
        ref_p = [(upper_b[i] + lower_b[i]) / 2.0 for i in range(len(upper_b))]

        response = {
            "response": {
                "reference_point": ref_p,
                "speed": 1,
                "go_to_previous": False,
                "stop": False,
                "user_bounds": [None, None, None],
            }
        }

        payload = json.dumps(response, ignore_nan=True)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
            data=payload,
        )

        assert response.status_code == 200

        content = json.loads(response.data)["response"]

        # iterated once
        assert content["step_number"] == 2

        # iterate till the end (add padding because we already iterate twice)
        responses = [None, None]
        for _ in range(98):
            response = self.app.post(
                "/method/control",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
                data=payload,
            )

            assert response.status_code == 200

            content = json.loads(response.data)["response"]
            responses.append(content)

        content = json.loads(response.data)["response"]

        assert content["step_number"] == 100
        assert content["steps_remaining"] == 1

        # take some steps back
        response = responses[58]
        response["go_to_previous"] = True
        response["reference_point"] = ref_p
        response["speed"] = 3
        response["stop"] = False
        response = {"response": response}

        payload = json.dumps(response, ignore_nan=True)

        response = self.app.post(
            "/method/control",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
            data=payload,
        )

        assert response.status_code == 200

        content = json.loads(response.data)["response"]

        assert content["step_number"] == 59
        assert content["steps_remaining"] == 42
"""