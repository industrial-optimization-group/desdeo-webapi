from app import db


class QuestionLikert(db.Model):
    __tablename__ = "question_likert"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("questionnaire.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    question_txt = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return (
            f"id: {self.id}, parent_id: {self.parent_id}, name: {self.name}, question: {self.question_txt}, "
            f"answer: {self.answer}"
        )


class QuestionOpen(db.Model):
    __tablename__ = "question_open"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("questionnaire.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    question_txt = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(1000), nullable=False)

    def __repr__(self):
        return (
            f"id: {self.id}, parent_id: {self.parent_id}, name: {self.name}, question: {self.question_txt}, "
            f"answer: {self.answer}"
        )


class Questionnaire(db.Model):
    __tablename__ = "questionnaire"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    description = db.Column(db.String(1000))
    date = db.Column(db.DateTime, nullable=False)

    questions_likert = db.relationship(QuestionLikert)
    questions_open = db.relationship(QuestionOpen)

    def __repr__(self):
        return (
            f"id: {self.id}, user_id: {self.user_id}, name: {self.name}, date: {self.date}, "
            f"likert children: {self.questions_likert}, open children: {self.questions_open}"
        )
