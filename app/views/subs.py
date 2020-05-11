""" Generic sub actions (creating subs, creating posts, etc) """
from peewee import fn
from flask import Blueprint, abort, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from .. import misc
from ..models import Sub, db as pdb
from ..forms import CreateSubTextPost, CreateSubForm, CreteSubPostCaptcha
bp = Blueprint('subs', __name__)


@bp.route("/submit/<ptype>", defaults={'sub': ''})
@bp.route("/submit/<ptype>/<sub>")
@login_required
def submit(ptype, sub):
    if ptype not in ['link', 'text', 'poll']:
        abort(404)

    if misc.get_user_level(current_user.uid)[0] <= 4:
        txtpostform = CreteSubPostCaptcha()
    else:
        txtpostform = CreateSubTextPost()
    txtpostform.ptype.data = ptype
    txtpostform.sub.data = sub
    if request.args.get('title'):
        txtpostform.title.data = request.args.get('title')
    if request.args.get('url'):
        txtpostform.link.data = request.args.get('url')
    if sub:
        try:
            dsub = Sub.get(fn.Lower(Sub.name) == sub.lower())
            return render_template('createpost.html', txtpostform=txtpostform, sub=dsub)
        except Sub.DoesNotExist:
            abort(404)
    else:
        return render_template('createpost.html', txtpostform=txtpostform)


@bp.route("/random")
def random_sub():
    """ Here we get a random sub """
    rsub = Sub.select(Sub.name).order_by(pdb.random()).limit(1)
    return redirect(url_for('sub.view_sub', sub=rsub.get().name))


@bp.route("/createsub")
@login_required
def create_sub():
    """ Here we can view the create sub form """
    createsub = CreateSubForm()
    return render_template('createsub.html', csubform=createsub)
