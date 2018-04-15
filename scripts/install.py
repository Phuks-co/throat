import __fix
import uuid
import bcrypt
from datetime import datetime
from app import app
from app.models import User, Client, Grant, Message, SiteLog, SiteMetadata, Sub, \
    SubFlair, SubLog, SubMetadata, SubPost, SubPostComment, \
    SubPostCommentVote, SubPostMetadata, SubPostVote, SubStylesheet, \
    SubSubscriber, Token, UserBadge, UserMetadata, UserSaved, \
    Pixel, Shekels, MiningLeaderboard, MiningSpeedLeaderboard, UserUploads, UserIgnores, \
    SubUploads

with app.app_context():
    print('Throat quick install script.')
    print(' Creating tables...')
    User.create_table(True)
    Client.create_table(True)
    Grant.create_table(True)
    Message.create_table(True)
    SiteLog.create_table(True)
    SiteMetadata.create_table(True)
    Sub.create_table(True)
    SubFlair.create_table(True)
    SubLog.create_table(True)
    SubMetadata.create_table(True)
    SubPost.create_table(True)
    SubPostComment.create_table(True)
    SubPostCommentVote.create_table(True)
    SubPostMetadata.create_table(True)
    SubPostVote.create_table(True)
    SubStylesheet.create_table(True)
    SubSubscriber.create_table(True)
    Token.create_table(True)
    UserBadge.create_table(True)
    UserMetadata.create_table(True)
    UserSaved.create_table(True)
    Pixel.create_table(True)
    Shekels.create_table(True)
    MiningLeaderboard.create_table(True)
    MiningSpeedLeaderboard.create_table(True)
    UserUploads.create_table(True)
    UserIgnores.create_table(True)
    SubUploads.create_table(True)
    print('Tables created.')

    print('Populating database...')
    user = User.create(name='admin', uid=uuid.uuid4(), joindate=datetime.utcnow(), crypto=1,
                       password=bcrypt.hashpw(b'adminadmin', bcrypt.gensalt()))
    UserMetadata.create(uid=user.uid, key='admin', value='1')
    print('ok')
