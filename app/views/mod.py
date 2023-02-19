""" Mod endpoints """
from peewee import fn
from flask import Blueprint, abort
from flask_login import login_required, current_user
from ..models import PostReportLog, CommentReportLog
from ..models import User, Sub, SubMod, SubPost, SubPostComment
from ..misc import engine, getModSubs, getReports
from ..forms import BanUserSubForm, CreateReportNote
from .. import misc
import json


bp = Blueprint("mod", __name__)


@bp.route("/")
@login_required
def index():
    """WIP: Mod Dashboard"""

    if not (
        SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin
    ):
        abort(404)

    subs = getModSubs(current_user.uid, 1)

    updated_subs = []

    for sub in subs:
        # get the sub sid
        this_sub = Sub.select().where(Sub.sid == sub.sid).get()
        sid = str(this_sub.sid)
        reports = getReports("mod", "all", 1, sid=sid)
        # add open_report_count and closed_report_count as properties on sub
        open_reports_count = reports["open_report_count"]
        closed_reports_count = reports["closed_report_count"]

        updated_sub = {
            "name": str(this_sub.name),
            "subscribers": str(this_sub.subscribers),
            "open_reports_count": open_reports_count,
            "closed_reports_count": closed_reports_count,
        }

        updated_subs += [updated_sub]
    return engine.get_template("mod/dashboard.html").render(
        {"subs": updated_subs, "sub": None, "subInfo": None, "subMods": None}
    )


@bp.route("/reports", defaults={"page": 1})
@bp.route("/reports/<int:page>")
@login_required
def reports(page):
    """WIP: Open Report Queue"""

    if not (
        SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin
    ):
        abort(404)

    reports = getReports("mod", "open", page)

    return engine.get_template("mod/reports.html").render(
        {
            "reports": reports,
            "page": page,
            "sub": False,
            "subInfo": False,
            "subMods": False,
        }
    )


@bp.route("/reports/closed", defaults={"page": 1})
@bp.route("/reports/closed/<int:page>")
@login_required
def closed(page):
    """WIP: Closed Reports List"""

    if not (
        SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin
    ):
        abort(404)

    reports = getReports("mod", "closed", page)

    return engine.get_template("mod/closed.html").render(
        {
            "reports": reports,
            "page": page,
            "sub": False,
            "subInfo": False,
            "subMods": False,
        }
    )


@bp.route("/reports/<sub>", defaults={"page": 1})
@bp.route("/reports/<sub>/<int:page>")
@login_required
def reports_sub(sub, page):
    """WIP: Sub Report Queue"""

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    subInfo = misc.getSubData(sub.sid)
    subMods = misc.getSubMods(sub.sid)

    if not (current_user.is_mod(sub.sid, 1) or current_user.is_admin()):
        abort(404)

    reports = getReports("mod", "open", page, sid=sub.sid)

    return engine.get_template("mod/sub_reports.html").render(
        {
            "sub": sub,
            "reports": reports,
            "page": page,
            "subInfo": subInfo,
            "subMods": subMods,
        }
    )


@bp.route("/reports/closed/<sub>", defaults={"page": 1})
@bp.route("/reports/closed/<sub>/<int:page>")
@login_required
def reports_sub_closed(sub, page):
    """WIP: Sub Closed Reports"""

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not (current_user.is_mod(sub.sid, 1) or current_user.is_admin()):
        abort(404)

    subInfo = misc.getSubData(sub.sid)
    subMods = misc.getSubMods(sub.sid)

    reports = getReports("mod", "closed", page, sid=sub.sid)

    return engine.get_template("mod/sub_reports_closed.html").render(
        {
            "sub": sub,
            "reports": reports,
            "page": page,
            "subInfo": subInfo,
            "subMods": subMods,
        }
    )


@bp.route("/reports/details/<sub>/<report_type>/<report_id>")
@login_required
def report_details(sub, report_type, report_id):
    """WIP: Report Details View"""

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        return abort(404)

    if not (current_user.is_mod(sub.sid, 1) or current_user.is_admin()):
        return abort(404)

    subInfo = misc.getSubData(sub.sid)
    subMods = misc.getSubMods(sub.sid)

    report = getReports("mod", "all", 1, type=report_type, report_id=report_id)
    reported_user = User.select().where(User.name == report["reported"]).get()
    related_reports = getReports(
        "mod", "all", 1, type=report_type, report_id=report_id, related=True
    )
    related_report_ids = [rep["id"] for rep in related_reports["query"]]

    if report["type"] == "post":
        try:
            post = misc.getSinglePost(report["pid"])
            comment = ""
            logs = (
                PostReportLog.select()
                .where(PostReportLog.rid == report["id"])
                .order_by(PostReportLog.lid.desc())
            )
        except SubPost.DoesNotExist:
            return abort(404)
    else:
        try:
            comment = (
                SubPostComment.select()
                .where(SubPostComment.cid == report["cid"])
                .dicts()[0]
            )
            post = ""
            logs = (
                CommentReportLog.select()
                .where(CommentReportLog.rid == report["id"])
                .order_by(CommentReportLog.lid.desc())
            )
        except (SubPostComment.DoesNotExist, IndexError):
            return abort(404)

    reported = User.select().where(User.name == report["reported"]).get()
    is_sub_banned = misc.is_sub_banned(sub, uid=reported.uid)

    return engine.get_template("mod/reportdetails.html").render(
        {
            "sub": sub,
            "report": report,
            "reported_user": reported_user,
            "related_reports": related_reports,
            "related_reports_json": json.dumps(related_report_ids, default=str),
            "banuserform": BanUserSubForm(),
            "is_sub_banned": is_sub_banned,
            "post": post,
            "comment": comment,
            "subInfo": subInfo,
            "subMods": subMods,
            "logs": logs,
            "createreportenote": CreateReportNote(),
        }
    )
