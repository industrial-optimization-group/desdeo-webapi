from database import db
import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.log_models import LogEntry, log_entry_types
from models.user_models import UserModel
import simplejson as json

log_entry_parser = reqparse.RequestParser()
log_entry_parser.add_argument(
    "entry_type",
    type=str,
    help=f"The type should be one of {log_entry_types}.",
    required=True,
)
log_entry_parser.add_argument(
    "data",
    type=str,
    help="Possible data associated with the log entry.",
    required=False,
)
log_entry_parser.add_argument(
    "info",
    type=str,
    help="Info associated with the log entry.",
    required=True,
)


class LogEntryResource(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        data = log_entry_parser.parse_args()

        log_entry_type = data["entry_type"]
        log_data = data["data"]
        log_info = data["info"]

        try:
            # create a new log entry
            log_entry = LogEntry(
                user_id=current_user_id,
                entry_type=log_entry_type,
                data=log_data,
                info=log_info,
                timestamp=datetime.datetime.now(),
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            print(
                f"DEBUG: Got an exception while creating a LogEntry POST request: {e}"
            )
            return {"message": "Could not add log entry."}, 500

        return {"message": "Log entry added successfully."}, 201