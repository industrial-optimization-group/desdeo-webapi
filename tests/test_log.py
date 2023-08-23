import datetime
import pytest
import json

from app import app
from database import db
from flask_testing import TestCase
from models.log_models import LogEntry
from models.user_models import UserModel


@pytest.mark.log
class TestLogging(TestCase):
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

    def test_log_model(self):
        username = "test_user"

        user_id = UserModel.query.filter_by(username=username).first().id

        timestamp = datetime.datetime.now()
        log_entry = LogEntry(
            user_id=user_id,
            entry_type="Info",
            timestamp=timestamp,
            data="This is data.",
            info="This is info.",
        )
        db.session.add(log_entry)

        log_entry_no_data = LogEntry(
            user_id=user_id,
            entry_type="Intermediate solution",
            timestamp=timestamp,
            info="This is an intermediate solution with no data.",
        )
        db.session.add(log_entry_no_data)

        log_entry_final = LogEntry(
            user_id=user_id,
            entry_type="Final solution",
            timestamp=timestamp,
            info="This is a final solution with data.",
            data="[1,2,3]",
        )
        db.session.add(log_entry_final)

        log_entry_preference = LogEntry(
            user_id=user_id,
            entry_type="Preference",
            timestamp=timestamp,
            info="This is a preference.",
            data="[3,2,1]",
        )
        db.session.add(log_entry_preference)

        db.session.commit()

        # check the entries
        entries = LogEntry.query.filter_by(user_id=user_id).all()
        assert len(entries) == 4

        assert entries[0].entry_type == "Info"
        assert entries[0].data == "This is data."
        assert entries[0].info == "This is info."
        assert entries[0].timestamp < datetime.datetime.now()

        assert entries[1].entry_type == "Intermediate solution"
        assert entries[1].data is None
        assert entries[1].info == "This is an intermediate solution with no data."
        assert entries[1].timestamp < datetime.datetime.now()

        assert entries[2].entry_type == "Final solution"
        assert entries[2].data == "[1,2,3]"
        assert entries[2].info == "This is a final solution with data."
        assert entries[2].timestamp < datetime.datetime.now()

        assert entries[3].entry_type == "Preference"
        assert entries[3].data == "[3,2,1]"
        assert entries[3].info == "This is a preference."
        assert entries[3].timestamp < datetime.datetime.now()

    def test_post_log(self):
        username = "test_user"
        atoken = self.login(uname=username)

        # create and entry to be sent to the server
        log_entry = {
            "entry_type": "Preference",
            "data": "[1,2,3]",
            "info": "This is a preference.",
        }

        payload = json.dumps(log_entry)

        response = self.app.post(
            "/log",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 201

        # check the entry is in the DB and that it is correct
        user_id = UserModel.query.filter_by(username=username).first().id
        entries = LogEntry.query.filter_by(user_id=user_id).all()
        assert len(entries) == 1

        assert entries[0].entry_type == "Preference"
        assert entries[0].data == "[1,2,3]"
        assert entries[0].info == "This is a preference."
        assert entries[0].timestamp < datetime.datetime.now()

        # create another entry
        log_entry = {
            "entry_type": "Intermediate solution",
            "data": "[1,1,2]",
            "info": "This is an intermediate solution.",
        }

        payload = json.dumps(log_entry)

        response = self.app.post(
            "/log",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atoken}",
            },
            data=payload,
        )

        assert response.status_code == 201

        entries = LogEntry.query.filter_by(user_id=user_id).all()
        assert len(entries) == 2

        assert entries[0].entry_type == "Preference"
        assert entries[0].data == "[1,2,3]"
        assert entries[0].info == "This is a preference."
        assert entries[0].timestamp < datetime.datetime.now()

        assert entries[1].entry_type == "Intermediate solution"
        assert entries[1].data == "[1,1,2]"
        assert entries[1].info == "This is an intermediate solution."
        assert entries[1].timestamp < datetime.datetime.now()