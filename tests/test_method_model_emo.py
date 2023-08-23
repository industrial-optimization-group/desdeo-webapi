import os

import numpy as np
import numpy.testing as npt
import pytest
import simplejson as json
from app import app
from database import db
from desdeo_problem.testproblems import test_problem_builder as problem_builder
from desdeo_emo.EAs import RVEA, IOPIS_NSGAIII
from desdeo_tools.interaction import (
    BoundPreference,
    NonPreferredSolutionPreference,
    PreferredSolutionPreference,
    ReferencePointPreference,
)
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
        db.drop_all()
        db.create_all()
        self.app = app.test_client()

        db.session.add(
            UserModel(username="test_user", password=UserModel.generate_hash("pass"))
        )
        db.session.commit()

        user_id = UserModel.query.filter_by(username="test_user").first().id

        # add DTLZ2 for test_user
        problem = problem_builder("DTLZ2", n_of_variables=5, n_of_objectives=4)
        db.session.add(
            Problem(
                name="DTLZ2",
                problem_type="Analytical",
                problem_pickle=problem,
                user_id=user_id,
                minimize="[1, 1, 1, 1]",
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

    def add_method(self, method_name):
        access_token = self.login()

        # fetch problem id
        problem_id = Problem.query.filter_by(name="DTLZ2").first().id

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

    def testCreateIRVEA(self):
        """Test that RVEA is properly created and added to the database via an HTTP call."""
        self.add_method("irvea")

        # fetch user id
        user_id = UserModel.query.filter_by(username="test_user").first().id

        # check method properly in DB
        method = Method.query.filter_by(user_id=user_id).first().method_pickle

        assert type(method).__name__ == RVEA.__name__

        # check it is interactive
        assert method.interact  # True

        # check the status of the method is proper
        method_status = Method.query.filter_by(user_id=user_id).first().status

        assert method_status == "NOT STARTED"

    def testStartIRVEA(self):
        access_token = self.login()
        self.add_method("irvea")

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Ok
        assert response.status_code == 200

        data = json.loads(response.data)

        # Check that preference type is unselected
        assert data["preference_type"] == -1

        # Check that the individuals (decision variables) are returned
        assert "individuals" in data
        assert len(data["individuals"]) > 0 and len(data["individuals"][0]) == 5

        # Check that the objectives are returned
        assert "objectives" in data
        assert len(data["objectives"]) > 0 and len(data["objectives"][0]) == 4

        # Check method status in DB
        method_q = Method.query.filter_by(id=1).first()
        method_status = method_q.status

        assert method_status == "ITERATING"

        # Check the status types in the database method object
        last_request = method_q.last_request

        #assert isinstance(last_request[0], PreferredSolutionPreference)
        #assert isinstance(last_request[1], NonPreferredSolutionPreference)
        #assert isinstance(last_request[2], ReferencePointPreference)
        #assert isinstance(last_request[3], BoundPreference)
        assert last_request.request_type == "reference_point_preference"

    def testIterateIRVEA(self):
        access_token = self.login()
        self.add_method("irvea")

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Ok
        assert response.status_code == 200

        def iterate(
            preference: list, preference_type: int, access_token: str = access_token
        ) -> dict:
            response = {
                "response": {"preference_data": preference},
                "preference_type": preference_type,
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

            return response

        # Iterate with no preferences
        preference_type = 0
        response = iterate(0, preference_type)

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert "preference_type" in data
        assert "individuals" in data
        assert "objectives" in data

        # Iterate with PreferredSolutionPreference
        preference_type = 1
        response = iterate([1, 2, 3], preference_type)

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert "preference_type" in data
        assert "individuals" in data
        assert "objectives" in data

        # Iterate with non-preferred solutionis preference
        preference_type = 2
        response = iterate([1, 2, 3], preference_type)

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert "preference_type" in data
        assert "individuals" in data
        assert "objectives" in data

        # Iterate with reference point
        preference_type = 3
        response = iterate([0.5, 0.5, 0.5, 0.5], preference_type)

        # OK
        assert response.status_code == 200

        # Iterate with bounds info
        preference_type = 4
        response = iterate(
            [[0.5, 0.7], [0.2, 0.5], [0.1, 0.5], [0.2, 0.6]], preference_type
        )

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert "preference_type" in data
        assert "individuals" in data
        assert "objectives" in data

        """# End
        preference_type = -1
        response = iterate(None, preference_type)

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "individuals" in data
        assert "objectives" in data"""

        # Bad preference_type
        preference_type = 42
        response = iterate(None, preference_type)

        assert response.status_code == 400

    def testCreateIOPIS(self):
        self.add_method("iopis")

        # fetch user id
        user_id = UserModel.query.filter_by(username="test_user").first().id

        # check method properly in DB
        method = Method.query.filter_by(user_id=user_id).first().method_pickle

        assert isinstance(method, IOPIS_NSGAIII)

        # check it is interactive
        assert method.interact  # True

        # check the status of the method is proper
        method_status = Method.query.filter_by(user_id=user_id).first().status

        assert method_status == "NOT STARTED"

    def testStartIOPIS(self):
        access_token = self.login()
        self.add_method("iopis")

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Ok
        assert response.status_code == 200

        data = json.loads(response.data)

        # Check that preference type is unselected
        assert data["preference_type"] == -1

        # Check that the individuals (decision variables) are returned
        assert "individuals" in data
        assert len(data["individuals"]) > 0 and len(data["individuals"][0]) == 5

        # Check that the objectives are returned
        assert "objectives" in data
        assert len(data["objectives"]) > 0 and len(data["objectives"][0]) == 4

        # Check method status in DB
        method_q = Method.query.filter_by(id=1).first()
        method_status = method_q.status

        assert method_status == "ITERATING"

        # Check the status types in the database method object
        last_request = method_q.last_request

        assert isinstance(last_request, ReferencePointPreference)

    def testIterateIOPIS(self):
        access_token = self.login()
        self.add_method("iopis")

        response = self.app.get(
            "/method/control",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Ok
        assert response.status_code == 200

        def iterate(preference: list, access_token: str = access_token) -> dict:
            response = {"response": {"preference_data": preference}}
            payload = json.dumps(response)

            response = self.app.post(
                "/method/control",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                data=payload,
            )

            return response

        # Iterate with reference point

        response = iterate([0.5, 0.5, 0.5, 0.5])

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert "preference_type" in data
        assert "individuals" in data
        assert "objectives" in data

        # End not implemented yet.
        """# End
        preference_type = -1
        response = iterate(None, preference_type)

        # OK
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "individuals" in data
        assert "objectives" in data"""
