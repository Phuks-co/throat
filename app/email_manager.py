from datetime import datetime, timedelta
from queue import Full
from time import sleep
from multiprocessing import Process, Queue
from typing import List, NamedTuple, Optional
from flask_babel import _
import logging

from .misc import url_for, slugify, send_email
from .models import Notification, Sub, SubPost, SubPostComment, User


class EmailInQueue(NamedTuple):
    email_to: List[str]
    email_subject: str
    email_text_content: str
    email_html_content: str
    email_sender: Optional[str] = None


class EmailManager:
    # Period in seconds user to poll pending unread notifications
    # ready to be forwarded via email
    secs_every: int
    # Oldest unread notification to include
    days_oldest: int
    # Queue processing pending emails to be sent
    q: Queue
    # Main queue producer
    producer: Process
    # Single queue consumer
    consumer: Process

    def __init__(self, secs_every=300, days_oldest=30):
        """
        Starts a child process that will run for
        the duration of the program, but not longer,
        while periodically checking for unread notifications
        to forward by email to users who've opted-in to
        this preference.
        """
        self.maxsize = 5000
        self.secs_every = secs_every
        self.days_oldest = days_oldest
        self.q = Queue(maxsize=self.maxsize)
        self.start()

    def _run_producer(self):
        # Periodically fetching and forwarding notifications via email
        self.producer = Process(target=self._produce)
        self.producer.start()

    def _run_consumer(self):
        # Forever consuming email queue
        self.consumer = Process(target=self._consume)
        self.consumer.start()

    def start(self):
        self._run_producer()
        self._run_consumer()

    def stop(self):
        if self.producer is not None and self.producer.is_alive():
            self.producer.terminate()
            self.producer.join()
            self.producer.close()

        if self.consumer is not None and self.consumer.is_alive():
            self.consumer.terminate()
            self.consumer.join()
            self.consumer.close()

    def _produce(self):
        """
        Periodically fetching and forwarding notifications
        for user who've opted-in to the feature
        """

        def get_post_link(i):
            return url_for("sub.view_post", sub=i.name, pid=i.pid)

        def get_comment_link(i):
            return url_for(
                "sub.view_perm",
                sub=i.sub,
                pid=i.pid,
                slug=slugify(i.title),
                cid=i.cid,
            )

        while True:
            sleep(self.secs_every)
            now = datetime.utcnow()
            before = now - timedelta(days=self.days_oldest)
            after = now - timedelta(seconds=self.secs_every)

            notifs_cursor = (
                Notification.select(
                    Notification.type,
                    Notification.sub,
                    Notification.post,
                    Notification.comment,
                    Notification.target,
                    Notification.created,
                    Sub.name,
                    SubPost.pid,
                    SubPost.title,
                    SubPost.link,
                    SubPostComment.cid,
                )
                .join(Sub)
                .join(SubPost)
                .join(SubPostComment)
                .where(
                    Notification.read.is_null(True) & before
                    < Notification.created & Notification.created
                    < after
                )
                .execute()
            )
            users_cursor = (
                User.select(User.name, User.email, User.uid)
                .where(User.opt_in_email_forwarded_notifications is True)
                .execute()
            )

            opt_ins = {user.uid: user for user in users_cursor}

            for notif in notifs_cursor:
                try:
                    if notif.target in opt_ins:
                        user_to = opt_ins[notif.target].email
                        user_name = opt_ins[notif.target].name
                        post_title = notif.title
                        link = ""
                        email_object = ""

                        if notif.type == "POST_REPLY":
                            email_object = _(
                                "a user has recently replied to a post of yours"
                            )
                            link = get_post_link(notif)
                        elif notif.type == "COMMENT_REPLY":
                            email_object = _(
                                "a user has recently replied to a comment of yours "
                            )
                            link = get_comment_link(notif)
                        elif notif.type == "POST_MENTION":
                            email_object = _(
                                "a user has recently mentioned a post of yours "
                            )
                            link = get_post_link(notif)
                        elif notif.type == "COMMENT_MENTION":
                            email_object = _(
                                "a user has recently mentioned a mention of yours "
                            )
                            link = get_comment_link(notif)

                        body = f"Dear {user_name}, {email_object} in the post {post_title}. Link: {link}"

                        # FIX ME: Mising HTML template...
                        self.schedule(
                            EmailInQueue(
                                user_to, email_object.capitalize(), body, ""
                            )  # <- ... as the last argument here
                        )
                except Exception:
                    continue

    def _consume(self):
        """Consuming email queue"""
        while True:
            email: EmailInQueue = self.q.get()
            try:
                send_email(
                    email.to,
                    email.subject,
                    email.text_content,
                    email.html_content,
                    email.sender,
                )
            except Exception:
                pass
            finally:
                self.q.task_done()
                sleep(0.01)

    def ensure_healthy(self):
        if self.producer is None or not self.producer.is_alive():
            self.producer = None
            self._run_producer()

        if self.consumer is None or not self.consumer.is_alive():
            self.consumer = None
            self._run_consumer()

    @property
    def is_healthy(self):
        if any(p is None for p in [self.producer, self.consumer]):
            return False
        try:
            return self.producer.is_alive() and self.consumer.is_alive()
        except ValueError:
            return False

    @property
    def enqueued(self):
        return self.q.qsize()

    def schedule(self, email: EmailInQueue):
        """Enqueuing items, healing producer & consumer along the way if needed"""
        try:
            self.ensure_healthy()
            self.q.put_nowait(email)
        except Full:
            counter = 0
            while len(self) >= self.maxsize:
                self.q.get_nowait()
                counter += 1
            self.q.put_nowait(email)
            logging.warning(
                f"Queue is full! Emptied and enqueued; {counter} pending email notifications were dropped."
            )
        except Exception:
            return
