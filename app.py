from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

api = Api(app)

ACCESS_EXPIRES = timedelta(hours=1)
app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "secret-key"
app.config["JWT_SECRET_KEY"] = "jwt-secret-key"
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES


jwt = JWTManager(app)

db = SQLAlchemy(app)


@app.before_first_request
def create_tables():
    db.create_all()


from models import user_models  # noqa: E402
from resources import problem_resources, user_resources  # noqa: E402

# import views


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = db.session.query(user_models.TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None


# Add user endpoints
api.add_resource(user_resources.UserRegistration, "/registration")
api.add_resource(user_resources.UserLogin, "/login")
api.add_resource(user_resources.UserLogoutAccess, "/logout/access")
api.add_resource(user_resources.UserLogoutRefresh, "/logout/refresh")
api.add_resource(user_resources.TokenRefresh, "/token/refresh")
api.add_resource(user_resources.AllUsers, "/users")
api.add_resource(user_resources.SecretResource, "/secret")

# Add problem endpoints
api.add_resource(problem_resources.ProblemCreation, "/problem/create")
