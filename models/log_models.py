from database import db
from sqlalchemy.orm import validates

log_entry_types = ["Intermediate solution", "Final solution", "Preference", "Info"]


class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.String(1000), nullable=True)
    info = db.Column(db.String(1000), nullable=False)

    def validate_type(self, _, type_):
        if type_ not in log_entry_types:
            raise ValueError(
                f"The given entry_type {type_} is not an acceptable type. Acceptable type are {log_entry_types}."
            )

        return type_

    def __repr__(self):
        return f"LogEntry(id: {self.id}, time: {self.timestamp}, data: {self.data}, info: {self.info})"