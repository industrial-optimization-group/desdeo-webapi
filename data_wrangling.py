from app import db

import pandas as pd

from models.user_models import UserModel
from models.log_models import LogEntry
from models.questionnaire_models import Questionnaire, QuestionOpen, QuestionLikert

if __name__ == "__main__":
    # get all user names
    users = db.session.query(UserModel).all()

    # select first user
    first_user = users[0]
    user_id = first_user.id

    # get all log entries
    log_entries = db.session.query(LogEntry).filter_by(user_id=user_id).order_by("timestamp").all()

    logs_df = pd.DataFrame([], columns=["timestamp", "entry_type", "info", "data"])

    logs = {
        "timestamp": [str(log.timestamp) for log in log_entries],
        "entry_type": [log.entry_type for log in log_entries],
        "info": [log.info for log in log_entries],
        "data": [log.data for log in log_entries]
    }

    #new_row = {"timestamp": [], "entry_type": ["Info", "Preference", "Data"], "info": [1,2,3], "data": ["hello", "I", "YES"]}

    logs_df = pd.DataFrame(logs)

    # logs_df.to_excel("logs.xlsx")

    # get all questionnaire entries
    q_entries = db.session.query(Questionnaire).filter_by(user_id=user_id).order_by("start_time").all()

    for q in q_entries:
        for l in q.questions_likert:
            print(l.name)
        for o in q.questions_open:
            print(o.name)

        
