from sqlalchemy import Column, Integer, String
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    """ Basic user data (Used for login or password recovery) """
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True)
    email = Column(String(128), unique=True)
    # In case we migrate to a different cipher for passwords
    # 1 = bcrypt
    crypto = Column(Integer)
    password = Column(String)
    # Account status
    # 0 = OK; 1 = banned; 2 = shadowbanned?; 3 = sent to oblivion?
    status = Column(Integer)
    
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.crypto = 1
        self.status = 0
        
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def __repr__(self):
        return '<User %r>' % self.username
