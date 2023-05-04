import json
import os
import datetime

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from app import app
from database import db
from desdeo_problem.problem import DiscreteDataProblem
from flask_testing import TestCase
from models.problem_models import Problem, SolutionArchive
from models.user_models import UserModel


@pytest.mark.analytical_problem
@pytest.mark.problem
class TestAnalyticalProblem(TestCase):
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
        db.session.add(
            UserModel(username="sad_user", password=UserModel.generate_hash("pass"))
        )
        db.session.commit()

        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
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
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        problem_def["name"] = "setup_test_problem_2"
        payload = json.dumps(problem_def)
        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        problem_def["name"] = "setup_test_problem_3"
        payload = json.dumps(problem_def)
        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 201

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_access_problem(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
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
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
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
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )

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
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
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
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
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
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # 400
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
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        assert response.status_code == 201

        # fetch problem and check
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

    def test_access_specific_problem(self):
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
        data = json.loads(response.data)

        access_token = data["access_token"]

        payload = json.dumps({"problem_id": 999})

        response = self.app.post(
            "/problem/access",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # 404
        # Problem with id 999 should not exist
        assert response.status_code == 404

        payload = json.dumps({"problem_id": 1})

        response = self.app.post(
            "/problem/access",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            data=payload,
        )

        # 200
        # Problem with id 1 should exis
        resp_dict = json.loads(response.data)
        orig_query = Problem.query.filter_by(name="setup_test_problem_1").first()
        orig_prob = orig_query.problem_pickle

        assert resp_dict["objective_names"] == orig_prob.get_objective_names()
        assert resp_dict["objective_names"] == orig_prob.get_objective_names()
        npt.assert_almost_equal(resp_dict["ideal"], orig_prob.ideal)
        npt.assert_almost_equal(resp_dict["nadir"], orig_prob.nadir)
        assert resp_dict["n_objectives"] == orig_prob.n_of_objectives
        assert resp_dict["problem_name"] == orig_query.name
        assert resp_dict["problem_type"] == orig_query.problem_type
        assert resp_dict["problem_id"] == orig_query.id
        npt.assert_almost_equal(resp_dict["minimize"], json.loads(orig_query.minimize))

        assert response.status_code == 200


@pytest.mark.discrete_problem
@pytest.mark.problem
class TestDiscreteProblem(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    TESTING = True

    def create_app(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = self.SQLALCHEMY_DATABASE_URI
        app.config["TESTING"] = self.TESTING
        return app

    def setUp(self):
        db.create_all()
        self.app = app.test_client()

        db.session.add(
            UserModel(username="test_user", password=UserModel.generate_hash("pass"))
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self):
        # login and get access token for test user
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
        data = json.loads(response.data)

        access_token = data["access_token"]

        return access_token

    def get_xs_and_fs(
        self,
        path=os.path.dirname(os.path.abspath(__file__)),
        fname="data/testPF_3f_11x_max.csv",
    ):
        pf = np.loadtxt(f"{path}/{fname}", delimiter=",")
        fs = list(map(list, pf[:, 0:3]))
        xs = list(map(list, pf[:, 3:]))

        return xs, fs

    def test_wrong_var_names(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # wrong n variables names
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3", "f4"],
                "variables": xs,
                "variable_names": ["x1", "x2", "x3", "x4"],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert (
            json.loads(response.data)["message"]
            == "The number of variable names does not match the one given in the data."
        )
        assert response.status_code == 406

    def test_wrong_obj_names(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # wrong n objective names
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3", "f4"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert (
            json.loads(response.data)["message"]
            == "The number of objective names does not match the one given in the data."
        )

        assert response.status_code == 406

    def test_bad_ideal(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # bad ideal
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
                "ideal": json.dumps([1, 1]),
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert (
            json.loads(response.data)["message"]
            == "The dimensions of the ideal point do not match with the number of objectives."
        )

        assert response.status_code == 406

    def test_bad_nadir(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()
        # bad nadir
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
                "ideal": [100, 100, 100],
                "nadir": [-100, -100, -100, -100],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert (
            json.loads(response.data)["message"]
            == "The dimensions of the nadir point do not match with the number of objectives."
        )

        assert response.status_code == 406

    def test_ideal_nadir_mismatch(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()
        # ideal and nadir given, but does not make sense
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
                "ideal": [100, 100, 100],
                "nadir": [100, 10, 1000],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert (
            "Given ideal and nadir are in conflict:"
            in json.loads(response.data)["message"]
        )

        assert response.status_code == 406

    def test_bad_minimize(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # bad minimize: wrong n items
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
                "ideal": [100, 100, 100],
                "nadir": [1000, 1000, 1000],
                "minimize": [1, 1],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert "Number of elements in minimize" in json.loads(response.data)["message"]

        assert response.status_code == 406

        # bad minimize: wrong element
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
                "ideal": [100, 100, 100],
                "nadir": [1000, 1000, 1000],
                "minimize": [1, 5, -1],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert "Some elements in" in json.loads(response.data)["message"]

        assert response.status_code == 406

    """
    def test_compute_ideal_and_nadir(self):
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # bad minimize: wrong element
        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": "discrete_test_problem",
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11"],
                "minimize": [1, 1, 1],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {atoken}"},
            data=payload,
        )

        assert "Some elements in" in json.loads(response.data)["message"]

        assert response.status_code == 406
    """

    def test_add_problem(self):
        # test that problem added to DB is correct
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()

        # check that no problems exists for current user
        response = self.app.get(
            "/problem/access",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert len(data["problems"]) == 0

        ptype = "Discrete"
        pname = "discrete_data_problem"
        uname = "test_user"
        objective_names = ["f1", "f2", "f3"]
        variable_names = [
            "x1",
            "x2",
            "x3",
            "x4",
            "x5",
            "x6",
            "x7",
            "x8",
            "x9",
            "x10",
            "x11",
        ]
        ideal = [100, 100, 100]
        nadir = [1000, 1000, 1000]
        minimize = [1, 1, 1]

        payload = json.dumps(
            {
                "problem_type": ptype,
                "name": pname,
                "objectives": fs,
                "objective_names": objective_names,
                "variables": xs,
                "variable_names": variable_names,
                "ideal": ideal,
                "nadir": nadir,
                "minimize": minimize,
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        data = json.loads(response.data)

        assert data["problem_type"] == ptype
        assert data["name"] == pname
        assert data["owner"] == uname

        assert response.status_code == 201

        # fetch problem and check it
        response = self.app.get(
            "/problem/access",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert len(data["problems"]) == 1

        problem_d = data["problems"][0]

        assert problem_d["name"] == pname
        assert problem_d["problem_type"] == ptype

        problem_id = problem_d["id"]

        payload = json.dumps(
            {
                "problem_id": problem_id,
            }
        )

        response = self.app.post(
            "/problem/access",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert data["objective_names"] == objective_names
        assert data["variable_names"] == variable_names
        assert data["ideal"] == ideal
        assert data["nadir"] == nadir
        assert data["n_objectives"] == len(objective_names)
        assert data["problem_name"] == pname
        assert data["problem_type"] == ptype
        assert data["problem_id"] == problem_id

        # check the query
        query = Problem.query.filter_by(name=pname).first()

        assert query.name == pname

        user_id = UserModel.query.filter_by(username="test_user").first().id

        assert query.user_id == user_id
        assert query.problem_type == ptype
        assert query.id == 1
        assert query.minimize == str(minimize)

        # check the pickle
        problem: DiscreteDataProblem = query.problem_pickle

        assert problem
        assert type(problem) is DiscreteDataProblem

        npt.assert_almost_equal(problem.objectives, fs)
        npt.assert_almost_equal(problem.decision_variables, xs)
        npt.assert_almost_equal(problem.ideal, ideal)
        npt.assert_almost_equal(problem.nadir, nadir)

        assert problem.n_of_objectives == len(objective_names)
        assert problem.objective_names == objective_names
        assert problem.variable_names == variable_names

    def test_compute_ideal_and_nadir(self):
        # test that problem the ideal and nadir are computed correctly if not given
        atoken = self.login()
        xs, fs = self.get_xs_and_fs()
        pname = "discrete_data_problem"

        ideal_true = np.min(fs, axis=0)
        nadir_true = np.max(fs, axis=0)

        assert ideal_true.shape[0] == 3
        assert nadir_true.shape[0] == 3

        payload = json.dumps(
            {
                "problem_type": "Discrete",
                "name": pname,
                "objectives": fs,
                "objective_names": ["f1", "f2", "f3"],
                "variables": xs,
                "variable_names": [
                    "x1",
                    "x2",
                    "x3",
                    "x4",
                    "x5",
                    "x6",
                    "x7",
                    "x8",
                    "x9",
                    "x10",
                    "x11",
                ],
            }
        )

        response = self.app.post(
            "/problem/create",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 201

        # fetch problem from DB
        query: Problem = Problem.query.filter_by(name=pname).first()

        problem = query.problem_pickle

        npt.assert_almost_equal(problem.ideal, ideal_true)
        npt.assert_almost_equal(problem.nadir, nadir_true)
        npt.assert_array_less(problem.ideal, problem.nadir)


@pytest.mark.archive
@pytest.mark.problem
class TestSolutionArchive(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    TESTING = True

    def create_app(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = self.SQLALCHEMY_DATABASE_URI
        app.config["TESTING"] = self.TESTING
        return app

    def setUp(self):
        db.create_all()
        self.app = app.test_client()

        db.session.add(
            UserModel(username="test_user", password=UserModel.generate_hash("pass"))
        )
        db.session.commit()

        self.addProblem()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def addProblem(self):
        path = os.path.dirname(os.path.abspath(__file__))
        fname = "data/testPF_3f_11x_max.csv"
        obj_names = [f"f_{i+1}" for i in range(3)]
        var_names = [f"x_{i+1}" for i in range(11)]
        df = pd.read_csv(f"{path}/{fname}", delimiter=",")
        df.iloc[:, 0:3] = -df.iloc[:, 0:3]
        df.columns = obj_names + var_names

        fs = df.to_numpy()[:, 0:3]
        ideal = np.min(fs, axis=1)
        nadir = np.max(fs, axis=1)

        problem = DiscreteDataProblem(df, var_names, obj_names, ideal, nadir)
        user_id = UserModel.query.filter_by(username="test_user").first().id

        db.session.add(
            Problem(
                name="test_problem",
                problem_type="Discrete",
                problem_pickle=problem,
                user_id=user_id,
                minimize="[1, 1, 1]",
            )
        )
        db.session.commit()

    def login(self):
        # login and get access token for test user
        payload = json.dumps({"username": "test_user", "password": "pass"})
        response = self.app.post(
            "/login", headers={"Content-Type": "application/json"}, data=payload
        )
        data = json.loads(response.data)

        access_token = data["access_token"]

        return access_token

    def test_add_solutions_to_db(self):
        dummy_vars = [[np.random.uniform() for _ in range(11)] for _ in range(10)]
        dummy_objs = [[3 * np.random.uniform() for _ in range(3)] for _ in range(10)]

        dict_data = {
            "variables": np.array(dummy_vars),
            "objectives": np.array(dummy_objs),
        }

        # get problem id
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        # add solutions to archive
        meta_data = "Testing the solution archive"
        date = datetime.datetime.now()
        db.session.add(
            SolutionArchive(
                problem_id=problem_id,
                solutions_dict_pickle=dict_data,
                meta_data=meta_data,
                date=date,
            )
        )

        db.session.commit()

        # check the db entry
        archive_query = SolutionArchive.query.filter_by(problem_id=problem_id).first()
        fetched_dict = archive_query.solutions_dict_pickle
        fetched_meta_data = archive_query.meta_data
        fetched_date = archive_query.date

        fetch_vars = fetched_dict["variables"]
        fetch_objs = fetched_dict["objectives"]

        npt.assert_almost_equal(fetch_vars, dummy_vars)
        npt.assert_almost_equal(fetch_objs, dummy_objs)

        assert fetched_meta_data == meta_data
        assert fetched_date == date

    def test_add_not_a_dict_to_db(self):
        dummy_vars = [[np.random.uniform() for _ in range(11)] for _ in range(10)]
        dummy_objs = [[3 * np.random.uniform() for _ in range(3)] for _ in range(10)]

        not_a_dict_data = [np.array(dummy_vars), np.array(dummy_objs)]

        # get problem id
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        # add solutions to archive
        with pytest.raises(ValueError) as err:
            db.session.add(
                SolutionArchive(
                    problem_id=problem_id, solutions_dict_pickle=not_a_dict_data
                )
            )

            assert "A dictionary must be supplied" in str(err.value)

    def test_add_dict_bad_keys_to_db(self):
        dummy_vars = [[np.random.uniform() for _ in range(11)] for _ in range(10)]
        dummy_objs = [[3 * np.random.uniform() for _ in range(3)] for _ in range(10)]

        dict_data_1 = {
            "variables": np.array(dummy_vars),
            "objectives_bad": np.array(dummy_objs),
        }

        # get problem id
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        with pytest.raises(ValueError) as err:
            db.session.add(
                SolutionArchive(
                    problem_id=problem_id, solutions_dict_pickle=dict_data_1
                )
            )

            assert "must contain the keys" in str(err.value)

        dict_data_2 = {
            "variables_bad": np.array(dummy_vars),
            "objectives": np.array(dummy_objs),
        }

        # get problem id
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        with pytest.raises(ValueError) as err:
            db.session.add(
                SolutionArchive(
                    problem_id=problem_id, solutions_dict_pickle=dict_data_2
                )
            )

            assert "must contain the keys" in str(err.value)

    def test_add_solutions(self):
        atoken = self.login()
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        # solutions to add
        dummy_vars = [list([np.random.uniform() for _ in range(11)]) for _ in range(3)]
        dummy_objs = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs),
                "variables": json.dumps(dummy_vars),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        # created
        assert response.status_code == 201

        # data = json.loads(response.data)

    def test_add_solutions_missing(self):
        atoken = self.login()
        problem_id = Problem.query.filter_by(name="test_problem").first().id

        # solutions to add
        dummy_vars = [list([np.random.uniform() for _ in range(11)]) for _ in range(3)]
        dummy_objs = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        # no objectives
        payload = json.dumps(
            {
                "problem_id": problem_id,
                "variables": json.dumps(dummy_vars),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "objectives" in data["errors"]

        # no variables
        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "variables" in data["errors"]

        # no problem id
        payload = json.dumps(
            {
                "objectives": json.dumps(dummy_objs),
                "variables": json.dumps(dummy_vars),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "problem_id" in data["errors"]

    def test_add_solutions_no_id(self):
        # add a bunch of problems
        [self.addProblem() for _ in range(10)]

        atoken = self.login()
        problem_id = 999

        # solutions to add
        dummy_vars = [list([np.random.uniform() for _ in range(11)]) for _ in range(3)]
        dummy_objs = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs),
                "variables": json.dumps(dummy_vars),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 404

        data = json.loads(response.data)
        assert str(problem_id) in data["message"]

    def test_add_solutions_existing(self):
        # add a bunch of problems
        [self.addProblem() for _ in range(10)]

        atoken = self.login()
        problem_id = 3

        # solutions to add
        dummy_vars_1 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_1 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 201

        # add more
        dummy_vars_2 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_2 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_2),
                "variables": json.dumps(dummy_vars_2),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 202

        # check the db
        dict_data = (
            SolutionArchive.query.filter_by(problem_id=problem_id)
            .first()
            .solutions_dict_pickle
        )

        npt.assert_almost_equal(dict_data["variables"], dummy_vars_1 + dummy_vars_2)

    def test_get_solutions(self):
        # add a bunch of problems
        [self.addProblem() for _ in range(3)]

        atoken = self.login()
        problem_id = 2

        # solutions to add
        dummy_vars_1 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(5)
        ]
        dummy_objs_1 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(5)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
            }
        )

        # add solutions through the API
        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 201

        # more to add
        dummy_vars_2 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(5)
        ]
        dummy_objs_2 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(5)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_2),
                "variables": json.dumps(dummy_vars_2),
            }
        )

        # add more solutions through the API
        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 202

        # fetch solutions
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 200

        data = json.loads(response.data)

        npt.assert_almost_equal(data["variables"], dummy_vars_1 + dummy_vars_2)
        npt.assert_almost_equal(data["objectives"], dummy_objs_1 + dummy_objs_2)

        assert "info" in data
        assert "date" in data

    def test_get_solutions_empty(self):
        # add a bunch of problems
        [self.addProblem() for _ in range(3)]

        atoken = self.login()
        problem_id = 3

        # fetch solutions
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert f"No archive found for problem with id {problem_id}" in data["message"]

    def test_get_solutions_no_problem(self):
        atoken = self.login()
        problem_id = 2

        # fetch solutions
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert f"No problem with id {problem_id}" in data["message"]

    def test_no_append_add(self):
        # add a bunch of problems
        [self.addProblem() for _ in range(10)]

        atoken = self.login()
        problem_id = 3

        # solutions to add
        dummy_vars_1 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_1 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 201

        # add more
        dummy_vars_2 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_2 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_2),
                "variables": json.dumps(dummy_vars_2),
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 202

        # check solutions
        payload = json.dumps(
            {
                "problem_id": problem_id,
            }
        )

        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 200

        data = json.loads(response.data)

        npt.assert_almost_equal(data["variables"], dummy_vars_1 + dummy_vars_2)
        npt.assert_almost_equal(data["objectives"], dummy_objs_1 + dummy_objs_2)

        # replace with new
        dummy_vars_new = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(10)
        ]
        dummy_objs_new = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(10)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_new),
                "variables": json.dumps(dummy_vars_new),
                "append": False,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 202

        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 200

        data = json.loads(response.data)

        npt.assert_almost_equal(data["variables"], dummy_vars_new)
        npt.assert_almost_equal(data["objectives"], dummy_objs_new)

    def test_no_append_add_no_existing(self):
        atoken = self.login()
        problem_id = 1

        # solutions to add
        dummy_vars_1 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_1 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
                "append": False,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 201

        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 200

        data = json.loads(response.data)

        npt.assert_almost_equal(data["variables"], dummy_vars_1)
        npt.assert_almost_equal(data["objectives"], dummy_objs_1)

    def test_info_and_date(self):
        # check that info and date is added correctly to solution archives
        atoken = self.login()
        problem_id = 1

        # solutions to add
        dummy_vars_1 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_1 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        info = "Testing the solution archive"
        time_added = datetime.datetime.now().replace(microsecond=0)
        # used when reading the date from GET
        date_format = "%d/%m/%Y -- %H:%M:%S"
        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
                "append": False,
                "info": info,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )
        assert response.status_code == 201

        # fetch the archive just added
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "info" in data
        assert "date" in data

        # check that the info is correct
        assert data["info"] == info

        # check that the date is earlier or the same as the date when the solution was first added.
        assert datetime.datetime.strptime(data["date"], date_format) == time_added

        # update the archive with new solutions and additional info

        dummy_vars_2 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_2 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        update_info = "Added new dummy solutions."
        update_time = datetime.datetime.now().replace(microsecond=0)

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_2),
                "variables": json.dumps(dummy_vars_2),
                "append": True,
                "info": update_info,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        # updated
        assert response.status_code == 202

        # get the newly updated archive
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "info" in data
        assert "date" in data

        # check that new info was appended as expected
        assert data["info"] == info + " " + update_info

        # check that the date was updated
        assert datetime.datetime.strptime(data["date"], date_format) >= time_added
        assert datetime.datetime.strptime(data["date"], date_format) == update_time

        # update the archive with new solutions and but no new info
        prev_info = data["info"]

        dummy_vars_2 = [
            list([np.random.uniform() for _ in range(11)]) for _ in range(3)
        ]
        dummy_objs_2 = [
            list([3 * np.random.uniform() for _ in range(3)]) for _ in range(3)
        ]

        update_no_info_time = datetime.datetime.now().replace(microsecond=0)

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_2),
                "variables": json.dumps(dummy_vars_2),
                "append": True,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        # updated
        assert response.status_code == 202

        # get the newly updated archive
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "info" in data
        assert "date" in data

        # info should now have changed
        assert data["info"] == prev_info

        # check that the date was updated
        assert (
            datetime.datetime.strptime(data["date"], date_format) >= update_no_info_time
        )

        # wipe old contents of a solution archive, check that info and date are updated accordingly

        wipe_info = "Wiped old archive, here are new solutions."
        wipe_time = datetime.datetime.now().replace(microsecond=0)

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
                "append": False,
                "info": wipe_info,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        # updated
        assert response.status_code == 202

        # get the new updated archive
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "info" in data
        assert "date" in data

        # chech the info and date
        assert data["info"] == wipe_info
        assert datetime.datetime.strptime(data["date"], date_format) >= wipe_time

        # wipe, but provide no new info

        wipe_no_info_time = datetime.datetime.now().replace(microsecond=0)

        payload = json.dumps(
            {
                "problem_id": problem_id,
                "objectives": json.dumps(dummy_objs_1),
                "variables": json.dumps(dummy_vars_1),
                "append": False,
            }
        )

        response = self.app.post(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        # updated
        assert response.status_code == 202

        # get the new updated archive
        payload = json.dumps({"problem_id": problem_id})
        response = self.app.get(
            "/archive",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 200

        data = json.loads(response.data)

        assert "info" in data
        assert "date" in data

        # chech the info and date
        ## should be empty string
        assert data["info"] == ""
        assert (
            datetime.datetime.strptime(data["date"], date_format) >= wipe_no_info_time
        )
