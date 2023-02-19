from bs4 import BeautifulSoup
from flask import url_for

from app.models import User

from test.utilities import csrf_token
from test.utilities import register_user, log_in_user, log_out_current_user


def substrings_present(data, snippets, exclude=False):
    """Return True if all the strings in `snippets` are found in `data`.
    If `exclude` is True, instead return True if none of the strings
    in `snippets` are found.

    """
    results = (snip.encode("utf-8") in data for snip in snippets)
    if exclude:
        results = (not val for val in results)
    return all(results)


def test_send_and_receive_pm(client, user_info, user2_info):
    """Send and receive a private message."""
    username = user_info["username"]
    register_user(client, user_info)
    register_user(client, user2_info)

    # User2 sends User a message.
    rv = client.get(url_for("user.view", user=username))
    assert rv.status == "200 OK"
    client.post(
        url_for("do.create_sendmsg"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            to=username,
            subject="Testing",
            content="Test Content",
        ),
        follow_redirects=True,
    )

    # User2 sees the message in Sent Messages.
    rv = client.get(url_for("messages.view_messages_sent"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(rv.data, [username, "Testing", "Test Content"])

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User has one new message.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "1"

    # User sees the message on the inbox page.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"]
    )

    # User marks the message as read.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find(lambda tag: tag.has_attr("data-mid"))
    mid = tag.attrs["data-mid"]

    rv = client.post(
        url_for("do.read_pm", mid=mid),
        data=dict(csrf_token=csrf_token(rv.data)),
    )

    # Re-logging to re-read the current_user data (in development mode this happens when reloading the page)
    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User returns to home page; notifications count now 0.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))

    assert link.get_text().strip() == "0"


def test_block_pm(client, user_info, user2_info):
    """Block and unblock private messages from a user."""
    username = user_info["username"]
    register_user(client, user_info)
    register_user(client, user2_info)

    # User2 sends User a message.
    rv = client.get(url_for("user.view", user=username))
    assert rv.status == "200 OK"
    client.post(
        url_for("do.create_sendmsg"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            to=username,
            subject="Testing",
            content="Test Content",
        ),
        follow_redirects=True,
    )

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User blocks User2.
    user2 = User.get(User.name == user2_info["username"])
    rv = client.post(
        url_for("do.ignore_user", uid=user2.uid),
        data=dict(csrf_token=csrf_token(rv.data)),
    )

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User doesn't have a notification for blocked message.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "0"

    # Message not visible in User's inbox.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"], exclude=True
    )

    # User2 shows up on User's ignore page.
    rv = client.get(url_for("user.view_ignores"))
    assert rv.status == "200 OK"
    assert user2_info["username"].encode("utf-8") in rv.data

    # User unblocks User2.
    rv = client.post(
        url_for("do.ignore_user", uid=user2.uid),
        data=dict(csrf_token=csrf_token(rv.data)),
    )

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User now has a notification for message.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "1"

    # Message now visible in User's inbox.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"]
    )


def test_save_and_delete_pm(client, user_info, user2_info):
    """Save and delete a private message."""
    username = user_info["username"]
    register_user(client, user_info)
    register_user(client, user2_info)

    # User2 sends User a message.
    rv = client.get(url_for("user.view", user=username))
    assert rv.status == "200 OK"
    client.post(
        url_for("do.create_sendmsg"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            to=username,
            subject="Testing",
            content="Test Content",
        ),
        follow_redirects=True,
    )

    # Switch users.
    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # Message visible in User's inbox.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"]
    )

    # User saves the message.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find(lambda tag: tag.has_attr("data-mid"))
    mid = tag.attrs["data-mid"]
    rv = client.post(
        url_for("do.save_pm", mid=mid),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )
    assert b"error" not in rv.data

    # Message now no longer appears in inbox.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"], exclude=True
    )

    # Message appears in saved messages.
    rv = client.get(url_for("messages.view_saved_messages"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"]
    )

    # User deletes message from saved messages.
    rv = client.post(
        url_for("do.delete_pm", mid=mid),
        data=dict(csrf_token=csrf_token(rv.data)),
        follow_redirects=True,
    )
    assert b"error" not in rv.data

    # Message is no longer in saved messages.
    rv = client.get(url_for("messages.view_saved_messages"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"], exclude=True
    )

    # Message is not in User's inbox either.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"], exclude=True
    )


def test_exchange_pm(client, user_info, user2_info):
    """Send a private message and have an exchange of replies."""
    username = user_info["username"]
    register_user(client, user_info)
    register_user(client, user2_info)

    # User2 sends User a message.
    rv = client.get(url_for("user.view", user=username))
    assert rv.status == "200 OK"
    rv = client.post(
        url_for("do.create_sendmsg"),
        data=dict(
            csrf_token=csrf_token(rv.data),
            to=username,
            subject="Testing",
            content="Test Content",
        ),
        follow_redirects=True,
    )
    assert b"error" not in rv.data

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User sees the message on the inbox page.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Testing", "Test Content"]
    )

    # User replies to the message.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find(lambda tag: tag.has_attr("data-mid"))
    mid = tag.attrs["data-mid"]

    rv = client.post(
        url_for("do.create_replymsg"),
        data=dict(
            csrf_token=csrf_token(rv.data), mid=mid, content="Test reply content"
        ),
    )
    assert b"error" not in rv.data

    # User sees the message in Sent Messages.
    rv = client.get(url_for("messages.view_messages_sent"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user2_info["username"], "Re: Testing", "Test reply content"]
    )

    log_out_current_user(client, verify=True)
    log_in_user(client, user2_info, expect_success=True)

    # User2 has one new message.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "1"

    # User2 sees the message on the inbox page.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user_info["username"], "Re: Testing", "Test reply content"]
    )

    # User2 replies to the reply.
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    tag = soup.find(lambda tag: tag.has_attr("data-mid"))
    mid = tag.attrs["data-mid"]
    rv = client.post(
        url_for("do.create_replymsg"),
        data=dict(
            csrf_token=csrf_token(rv.data), mid=mid, content="Test 2nd reply content"
        ),
    )
    assert b"error" not in rv.data

    # User2 sees reply in Sent Messages.
    rv = client.get(url_for("messages.view_messages_sent"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert substrings_present(
        rv.data, [user_info["username"], "Re: Testing", "Test 2nd reply content"]
    )
    assert b"Re: Re: Testing" not in rv.data

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User now has two new messages.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "2"

    # User sees the message on the inbox page.
    rv = client.get(url_for("messages.inbox_sort"), follow_redirects=True)
    assert rv.status == "200 OK"
    assert b"Test 2nd reply content" in rv.data

    # User uses the mark all as read link.
    rv = client.post(url_for("do.readall_msgs"), data={})
    assert b"error" not in rv.data

    log_out_current_user(client, verify=True)
    log_in_user(client, user_info, expect_success=True)

    # User now has no new messages.
    rv = client.get(url_for("home.index"), follow_redirects=True)
    assert rv.status == "200 OK"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.find(href=url_for("messages.inbox_sort"))
    assert link.get_text().strip() == "0"
