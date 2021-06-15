from typing import Type, TypeVar

import factory
from peewee import Model

from app.models import SiteMetadata, Sub, SubPost, User, UserMetadata

T = TypeVar("T", bound=Model)


class PeeweeBaseFactory(factory.Factory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class: Type[T], *args, **kwargs) -> T:
        return model_class.create(*args, **kwargs)


class SubFactory(PeeweeBaseFactory):
    class Meta:
        model = Sub

    name = factory.Faker("word")


class UserFactory(PeeweeBaseFactory):
    class Meta:
        model = User

    uid = factory.Faker("uuid4")
    name = factory.Faker("user_name")
    crypto = 0


def promote_user_to_admin(user: User) -> None:
    UserMetadata.create(uid=user.uid, key="admin", value="1")


class AdminFactory(UserFactory):
    class Meta:
        model = User

    @classmethod
    def _create(cls, model_class: Type[User], *args, **kwargs) -> User:
        user = super()._create(model_class, *args, **kwargs)
        promote_user_to_admin(user)
        return user


class PostFactory(PeeweeBaseFactory):
    class Meta:
        model = SubPost

    sid = factory.SubFactory(SubFactory)
    title = factory.Faker("sentence")
    comments = 0
    uid = factory.SubFactory(UserFactory)


class AnnouncedPostFactory(PostFactory):
    @classmethod
    def _create(cls, model_class: Type[SubPost], *args, **kwargs) -> SubPost:
        post = super()._create(model_class, *args, **kwargs)
        SiteMetadata.create(key="announcement", value=post.pid)
        return post
