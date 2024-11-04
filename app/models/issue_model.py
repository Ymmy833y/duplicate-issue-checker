from app import db

class Issue(db.Model):
    __tablename__ = 'issues'

    name = db.Column(db.String, primary_key=True)
    number = db.Column(db.Integer, primary_key=True)
    comments = db.Column(db.PickleType)
    embedding = db.Column(db.LargeBinary, nullable=False)
    shape = db.Column(db.String, nullable=False)
    updated = db.Column(db.String, nullable=False)

    __table_args__ = (
        db.PrimaryKeyConstraint('name', 'number'),
    )
