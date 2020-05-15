""" Generic sub actions (creating subs, creating posts, etc) """
import uuid
from peewee import fn
from flask import Blueprint, abort, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..config import config
from ..misc import engine
from ..models import Sub, db as pdb, SubMod, SubMetadata, SubStylesheet, SubSubscriber
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


@bp.route("/createsub", methods=['GET', 'POST'])
@login_required
def create_sub():
    """ Here we can view the create sub form """
    form = CreateSubForm()
    # return engine.get_template('sub/create.html').render({'csubform': createsub})
    if not form.validate():
        return engine.get_template('sub/create.html').render({'error': misc.get_errors(form, True), 'csubform': form})

    if not misc.allowedNames.match(form.subname.data):
        return engine.get_template('sub/create.html').render(
            {'error': _('Sub name has invalid characters'), 'csubform': form})

    if form.subname.data.lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):
        return engine.get_template('sub/create.html').render({'error': _('Invalid sub name'), 'csubform': form})

    try:
        Sub.get(fn.Lower(Sub.name) == form.subname.data.lower())
        return engine.get_template('sub/create.html').render(
            {'error': _('Sub is already registered'), 'csubform': form})
    except Sub.DoesNotExist:
        pass

    level = misc.get_user_level(current_user.uid)[0]
    if not config.app.testing and config.site.sub_creation_min_level != 0:
        if (level <= 1) and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _("You must be at least level %(level)i.", level=config.site.sub_creation_min_level),
                 'csubform': form})

        owned = SubMod.select().where(SubMod.uid == current_user.uid).where(
            (SubMod.power_level == 0) & (SubMod.invite == False)).count()

        if owned >= 20 and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _('You cannot own more than %(max)i subs.', max=config.site.sub_ownership_limit),
                 'csubform': form})

        if owned >= (level - 1) and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _('You cannot own more than %(max)i subs. Try leveling up your account.',
                            max=config.site.sub_ownership_limit),
                 'csubform': form})

    sub = Sub.create(sid=uuid.uuid4(), name=form.subname.data, title=form.title.data)
    SubMetadata.create(sid=sub.sid, key='mod', value=current_user.uid)
    SubMod.create(sid=sub.sid, uid=current_user.uid, power_level=0)
    SubStylesheet.create(sid=sub.sid, content='', source='/* CSS here */')

    # admin/site log
    misc.create_sublog(misc.LOG_TYPE_SUB_CREATE, uid=current_user.uid, sid=sub.sid, admin=True)

    SubSubscriber.create(uid=current_user.uid, sid=sub.sid, status=1)

    return redirect(url_for('sub.view_sub', sub=form.subname.data))
