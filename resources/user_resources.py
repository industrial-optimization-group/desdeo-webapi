from datetime import datetime, timezone
import random
import string
from functools import wraps
import json
import numpy as np

from database import db
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.user_models import TokenBlocklist, UserModel, GuestUserModel, role_required, USER_ROLE, GUEST_ROLE
from models.problem_models import GuestProblem
from desdeo_problem.testproblems import car_side_impact, vehicle_crashworthiness, river_pollution_problem

def make_river_with_ideal_and_nadir():
    problem = river_pollution_problem()
    problem.ideal = np.array([-6.34, -3.44, -7.5, 0, 0])
    problem.nadir = np.array([-4.75, -2.85, -0.32, 9.70, 0.35])
    return problem


default_problems = {"car_side_impact": car_side_impact(), "vehicle_crash_worthiness": vehicle_crashworthiness(), "river_pollution_w_ideal_and_nadir": make_river_with_ideal_and_nadir()}

user_parse = reqparse.RequestParser()
user_parse.add_argument("username", help="The username is required", required=True)
user_parse.add_argument("password", help="The password is required", required=True)

class GuestCreate(Resource):
    """To request a new user account"""
    def get(self):
        # Create a random guest username
        username = f"guest_{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))}"

        # Check that is does not exists yet, retry if it does
        if GuestUserModel.find_by_username(username):
            while GuestUserModel.find_by_username(username):
                username = f"guest_{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))}"

        # Add guest to database and create tokens
        new_guest = GuestUserModel(username=username)
        try:
            db.session.add(new_guest)
            db.session.commit()

            additional_claims = {"role": GUEST_ROLE}
            access_token = create_access_token(username, additional_claims=additional_claims)
            refresh_token = create_refresh_token(username)
        except Exception as e:
            return {"message": "Could not add new guest to database"}, 500

        # create and add problems for guest to database
        try:
            for problem_name, problem in default_problems.items():
                db.session.add(
                    GuestProblem(
                        name=problem_name,
                        problem_type="Test problem",
                        problem_pickle=problem,
                        user_id=new_guest.id,
                        minimize=json.dumps([1 for _ in range(problem.n_of_objectives)]),
                    )
                )
                db.session.commit()
        except Exception as e:
            return {"message": "Could not add default problems to guest user"}, 500

        return {
            "message": f"Guest {username} was created!",
            "access_token": access_token,
            "refresh_token": refresh_token,
        }, 200

class UserRegistration(Resource):
    def post(self):
        data = user_parse.parse_args()

        if UserModel.find_by_username(data["username"]):
            return {"message": f"User {data['username']} already exists!"}, 400

        new_user = UserModel(username=data["username"], password=UserModel.generate_hash(data["password"]))
        try:
            new_user.save_to_db()
            additional_claims = {"role": USER_ROLE}
            access_token = create_access_token(identity=data["username"], additional_claims=additional_claims)
            refresh_token = create_refresh_token(identity=data["username"])
            return {
                "message": f"User {data['username']} was created!",
                "access_token": access_token,
                "refresh_token": refresh_token,
            }, 200
        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": "Something went wrong"}, 500


class UserLogin(Resource):
    def post(self):
        data = user_parse.parse_args()
        current_user = UserModel.find_by_username(data["username"])

        if not current_user:
            return {"message": f"User {data['username']} does not exist!"}, 401

        try:
            if UserModel.verify_hash(data["password"], current_user.password):
                additional_claims = {"role": USER_ROLE}
                access_token = create_access_token(identity=data["username"], additional_claims=additional_claims)
                refresh_token = create_refresh_token(identity=data["username"])
                return {
                    "message": f"Logged as {current_user.username}",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }, 200
        except Exception as e:
            print(f"DEBUG: {e}")
            return {"message": "Something went wrong."}, 500

        else:
            return {"message": "Wrong credentials"}, 401


class UserLogoutAccess(Resource):
    @jwt_required()
    @role_required(USER_ROLE)
    def post(self):
        try:
            claims = get_jwt()
            now = datetime.now(timezone.utc)
            db.session.add(TokenBlocklist(jti=claims["jti"], created_at=now))
            db.session.commit()
            return {"message": "Access token revoked"}, 200
        except Exception as e:
            print(f"DEBUG {e}")
            return {"message": "Something went wrong while revoking an access token."}, 500


class UserLogoutRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        try:
            claims = get_jwt()
            jti = claims["jti"]
            now = datetime.now(timezone.utc)
            db.session.add(TokenBlocklist(jti=jti, created_at=now))
            db.session.commit()
            return {"message": "Refresh token revoked"}
        except Exception as e:
            print(f"DEBUG {e}")
            return {"message": "Something went wrong while revoking an refresh token."}, 500


class TokenRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        additional_claims = {"role": USER_ROLE}
        access_token = create_access_token(identity=current_user, additional_claims=additional_claims)
        return {"access_token": access_token}


class AllUsers(Resource):
    def get(self):
        return UserModel.return_all()

    def delete(self):
        return UserModel.delete_all()


class SecretResource(Resource):
    """Used for testing."""
    @jwt_required()
    @role_required(USER_ROLE)
    def get(self):
        return {"answer": 42}
