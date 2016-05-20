#!/usr/bin/env python3
# -*- coding: utf-8
""" Here is where all the good stuff happens """

import json
import bcrypt
from flask import Flask, render_template, session, redirect, url_for, abort
from models import db, User, Sub

import config
from forms import RegistrationForm, LoginForm, LogOutForm, CreateSubForm
import forms


app = Flask(__name__)

app.jinja_env.globals.update(forms=forms)
app.config.from_object(config)

db.init_app(app)


@app.before_first_request
def initialize_database():
    """ This is executed before any request is processed. We use this to
    create all the tables and database shit we need. """
    db.create_all()


@app.context_processor
def utility_processor():
    """ Here we set some useful stuff for templates """
    if 'user' not in session:
        register = RegistrationForm()
        login = LoginForm()
        return {'loginform': login, 'regform': register}
    else:
        logout = LogOutForm()
        createsub = CreateSubForm()
        return {'logoutform': logout, 'csubform': createsub}


@app.route("/")
def index():
    """ The index page """
    return render_template('index.html')


def get_errors(form):
    """ A simple function that returns a list with all the form errors. """
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret


@app.route("/do/logout", methods=['POST'])
def do_logout():
    """ Logout endpoint """
    form = LogOutForm()
    if form.validate():
        session.pop('user', None)
    return redirect(url_for('index'))


@app.route("/do/login", methods=['POST'])
def do_login():
    """ Login endpoint """
    form = LoginForm()
    if form.validate():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist.']})

        if user.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode(), user.password)
            if thash == user.password:
                session['user'] = user.uid
                return json.dumps({'status': 'ok'})
            else:
                return json.dumps({'status': 'error',
                                   'error': ['Invalid password.']})
        else:
            return json.dumps({'status': 'error',
                               'error': ['Unknown password hash']})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/register", methods=['POST'])
def do_register():
    """ Registration endpoint """
    form = RegistrationForm()
    if form.validate():
        # check if user or email are in use
        if User.query.filter_by(username=form.username.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Username is already registered.']})
        if User.query.filter_by(email=form.email.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Email is alredy in use.']})
        user = User(form.username.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/create_sub", methods=['POST'])
def create_sub():
    """ Sub creation endpoint """
    form = CreateSubForm()
    if form.validate():
        if Sub.query.filter_by(name=form.subname.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Sub is already registered.']})

        sub = Sub(form.subname.data, form.title.data)
        db.session.add(sub)
        db.session.commit()
        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=form.subname.data)})

    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/s/<sub>")
def view_sub(sub):
    """ Here we can view subs """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)
    return render_template('sub.html', sub=sub.name, sub_title=sub.title)


@app.errorhandler(403)
def Forbidden(error):
    """ 403 Forbidden """
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(error):
    """ 404 Not found error """
    return render_template('errors/404.html'), 404


@app.errorhandler(418)
def teapot(error):
    """ 404 I'm a teapot """
    return render_template('errors/418.html'), 404


@app.errorhandler(500)
def server_error(error):
    """ 500 Internal server error """
    return render_template('errors/500.html'), 500

if __name__ == "__main__":
    app.run()
