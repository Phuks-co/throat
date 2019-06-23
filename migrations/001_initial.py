"""Peewee migrations -- 001_initial.py.

Initial migration file 
Creates all the tables required to have an operational instance
"""

from app.models import User, Client, Grant, Message, SiteLog, SiteMetadata, Sub, \
    SubFlair, SubLog, SubMetadata, SubPost, SubPostComment, \
    SubPostCommentVote, SubPostMetadata, SubPostVote, SubStylesheet, \
    SubSubscriber, Token, UserMetadata, UserSaved, \
    UserUploads, UserIgnores, SubPostCommentReport, \
    SubUploads, SubPostPollOption, SubPostPollVote, SubPostReport, APIToken, APITokenSettings


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    migrator.create_model(User)
    migrator.create_model(UserMetadata)
    migrator.create_model(UserIgnores)
    migrator.create_model(UserSaved)

    migrator.create_model(Sub)
    migrator.create_model(SubLog)
    migrator.create_model(SubStylesheet)
    migrator.create_model(SubSubscriber)
    migrator.create_model(SubFlair)
    migrator.create_model(SubMetadata)
    migrator.create_model(SubUploads)
    migrator.create_model(SubPost)
    migrator.create_model(SubPostMetadata)
    migrator.create_model(SubPostVote)
    migrator.create_model(SubPostReport)
    migrator.create_model(SubPostPollOption)
    migrator.create_model(SubPostPollVote)
    migrator.create_model(SubPostComment)
    migrator.create_model(SubPostCommentReport)
    migrator.create_model(SubPostCommentVote)

    migrator.create_model(UserUploads)
    
    migrator.create_model(SiteMetadata)
    migrator.create_model(SiteLog)
    
    migrator.create_model(Message)
    
    migrator.create_model(Client)
    migrator.create_model(Grant)
    migrator.create_model(Token)

    migrator.create_model(APIToken)
    migrator.create_model(APITokenSettings)

