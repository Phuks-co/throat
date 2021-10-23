import json
from bs4 import BeautifulSoup
from flask import url_for

from app.config import config
from test.utilities import (
    create_sub,
    csrf_token,
    log_in_user,
    log_out_current_user,
    register_user,
)


def test_comment_sort(client, user_info):
    "Comments can be sorted by best, top and new."
    config.update_value("site.sub_creation_min_level", 0)

    # Create a mod and a sub.
    mod = user_info
    register_user(client, mod)
    create_sub(client)
    log_out_current_user(client)

    # Create some users to read and vote.
    users = [
        dict(username=f"user{i}", email=f"user{i}@example.com", password="password")
        for i in range(10)
    ]
    for user in users:
        register_user(client, user)
        log_out_current_user(client)

    # Mod makes a post and adds three comments to it.
    log_in_user(client, mod)
    rv = client.get(url_for("subs.submit", ptype="text", sub="test"))
    csrf = csrf_token(rv.data)
    data = {
        "csrf_token": csrf,
        "title": "the title",
        "ptype": "text",
        "content": "the content",
    }
    rv = client.post(
        url_for("subs.submit", ptype="text", sub="test"),
        data=data,
        follow_redirects=False,
    )
    assert rv.status == "302 FOUND"
    soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
    link = soup.a.get_text()
    pid = link.split("/")[-1]

    rv = client.get(link, follow_redirects=True)
    assert b"the title |  test" in rv.data
    cids = {}
    for comment in ["oldest", "middle", "newest"]:
        data = {
            "csrf_token": csrf,
            "post": pid,
            "parent": "0",
            "comment": "This comment is: " + comment,
        }
        rv = client.post(
            url_for("do.create_comment", pid=pid), data=data, follow_redirects=False
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"
        cids[comment] = reply["cid"]
    log_out_current_user(client)

    # The other users visit and vote the comments as follows:
    # oldest - 10 visits, 5 upvotes, 1 downvote
    # middle - 2 visits, 2 upvotes
    # newest - 0 visits, 0 upvotes
    expected_results = {
        "new": ["newest", "middle", "oldest"],
        "top": ["oldest", "middle", "newest"],
        "best": ["middle", "newest", "oldest"],
    }

    for num, user in enumerate(users):
        log_in_user(client, user)

        # View some comments.
        if num < 2:
            views = [cids["oldest"], cids["middle"]]
        else:
            views = [cids["oldest"]]
        rv = client.post(
            url_for("do.mark_comments_viewed"),
            data={"csrf_token": csrf, "cids": json.dumps(views)},
        )
        reply = json.loads(rv.data.decode("utf-8"))
        assert reply["status"] == "ok"

        # Upvote some comments.
        if num < 5:
            rv = client.post(
                url_for("do.upvotecomment", cid=cids["oldest"], value="up"),
                data={"csrf_token": csrf},
            )
            assert rv.status == "200 OK"

        if num < 2:
            rv = client.post(
                url_for("do.upvotecomment", cid=cids["middle"], value="up"),
                data={"csrf_token": csrf},
            )
            assert rv.status == "200 OK"

        # Downvote a comment
        if num == 0:
            rv = client.post(
                url_for("do.upvotecomment", cid=cids["oldest"], value="down"),
                data={"csrf_token": csrf},
            )
            assert rv.status == "200 OK"

        log_out_current_user(client)

    for sort, order in expected_results.items():
        rv = client.get(
            url_for("sub.view_post", pid=pid, sub="test", slug="", sort=sort),
            follow_redirects=True,
        )
        assert rv.status == "200 OK"
        soup = BeautifulSoup(rv.data, "html.parser", from_encoding="utf-8")
        comments = [c.get_text() for c in soup.find_all("div", class_="content")]
        for expected, comment in zip(order, comments):
            assert comment.find(expected) != -1
