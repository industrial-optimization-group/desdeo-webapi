from datetime import datetime, timezone

from app import db
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource, reqparse
from models.user_models import TokenBlocklist, UserModel

parser = reqparse.RequestParser()
parser.add_argument("username", help="The username is required", required=True)
parser.add_argument("password", help="The password is required", required=True)


class UserRegistration(Resource):
    def post(self):
        data = parser.parse_args()

        if UserModel.find_by_username(data["username"]):
            return {"message": f"User {data['username']} already exists!"}, 400

        new_user = UserModel(username=data["username"], password=UserModel.generate_hash(data["password"]))
        try:
            new_user.save_to_db()
            access_token = create_access_token(identity=data["username"])
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
        data = parser.parse_args()
        current_user = UserModel.find_by_username(data["username"])

        if not current_user:
            return {"message": f"User {data['username']} does not exist!"}, 401

        try:
            if UserModel.verify_hash(data["password"], current_user.password):
                access_token = create_access_token(identity=data["username"])
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
    def post(self):
        try:
            jti = get_jwt()["jti"]
            now = datetime.now(timezone.utc)
            db.session.add(TokenBlocklist(jti=jti, created_at=now))
            db.session.commit()
            return {"message": "Access token revoked"}, 200
        except Exception as e:
            print(f"DEBUG {e}")
            return {"message": "Something went wrong while revoking an access token."}, 500


class UserLogoutRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        try:
            jti = get_jwt()["jti"]
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
        access_token = create_access_token(identity=current_user)
        return {"access_token": access_token}


class AllUsers(Resource):
    def get(self):
        return UserModel.return_all()

    def delete(self):
        return UserModel.delete_all()


class SecretResource(Resource):
    @jwt_required()
    def get(self):
        return {"answer": 42}
