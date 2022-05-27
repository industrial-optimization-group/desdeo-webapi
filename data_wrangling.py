from app import db

import datetime

import ast

import pandas as pd

from models.user_models import UserModel
from models.log_models import LogEntry
from models.questionnaire_models import Questionnaire, QuestionOpen, QuestionLikert

if __name__ == "__main__":
    # get all user names
    users = db.session.query(UserModel).all()

    n_users = 30

    for i in range(n_users):
        # select first user
        first_user = users[i]
        user_id = first_user.id
        username = first_user.username

        if username == "enautilus_2":
            continue

        # get all log entries
        log_entries = db.session.query(LogEntry).filter_by(user_id=user_id).order_by("timestamp").all()

        logs_df = pd.DataFrame([], columns=["timestamp", "entry_type", "info", "data"])

        logs = {
            "timestamp": [str(log.timestamp) for log in log_entries],
            "entry_type": [log.entry_type for log in log_entries],
            "info": [log.info for log in log_entries],
            "data": [ast.literal_eval(log.data.replace("true", "True").replace("false", "False")) if log.data else None for log in log_entries]
        }

        logs_df = pd.DataFrame(logs)

        logs_df.to_excel(f"./logs/{username}_logs.xlsx")

        # get all questionnaire entries
        q_entries = db.session.query(Questionnaire).filter_by(user_id=user_id).order_by("start_time").all()

        qasl = []

        for q in q_entries:
            elapsed_time = round((q.completion_time - q.start_time).total_seconds(), 2)
            qas = {"Questionnaire name": q.name} 
            qas["description"] = q.description
            qas["start_time"] = q.start_time
            qas["completion_time"] = q.completion_time
            qas["time_elapsed"] = elapsed_time
            for lq in q.questions_likert:
                qas[lq.name] = lq.answer
            for oq in q.questions_open:
                qas[oq.name] = oq.answer

            qasl.append(qas)

        qas_df = pd.DataFrame(qasl)

        qas_df.to_excel(f"./logs/{username}_answers.xlsx")