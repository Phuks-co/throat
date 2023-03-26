from app.email_manager import EmailInQueue, EmailManager
from contextlib import contextmanager


@contextmanager
def email_manager(*args, **kwargs):
    email_manager = EmailManager()
    try:
        yield email_manager
    finally:
        email_manager.stop()


def test_launching():
    with email_manager() as em:
        assert em.is_healthy


def test_enqueuing():
    one = EmailInQueue(["alice@people.ex"], "subject or object?", "Hello", "")
    two = EmailInQueue(["bob@people.ex"], "object or subject?", "World", "")
    with email_manager() as em:
        em.schedule(one)
        em.schedule(two)
        assert em.enqueued == 2


def test_stopping():
    email_manager = EmailManager()
    email_manager.stop()
    assert not email_manager.is_healthy
