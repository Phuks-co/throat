#!/usr/bin/env python3
# -*- coding: utf-8

from flask import Flask, render_template, flash, request, session, redirect, url_for
from models import db, User
import config
import json
import bcrypt
from forms import RegistrationForm, LoginForm, LogOutForm

app = Flask(__name__)

app.config.from_object(config)

db.init_app(app)

@app.before_first_request
def initialize_database():
    db.create_all()

@app.route("/")
def index():
    if 'user' not in session:
        register = RegistrationForm()
        login = LoginForm()
        return render_template('index.html', regform=register, loginform=login)
    else:
        logout = LogOutForm()
        return render_template('index.html', logoutform=logout)

def get_errors(form):
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret

@app.route("/do/logout", methods=['POST'])
def do_logout():
    form = LogOutForm()
    if form.validate():
        session.pop('user', None)
    return redirect(url_for('index'))

@app.route("/do/login", methods=['POST'])
def do_login():
    form = LoginForm()
    if form.validate():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            return json.dumps({'status': 'error', 'error': ['User does not exist.']})
        
        if user.crypto == 1: # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode(), user.password)
            if thash == user.password:
                session['user'] = user.id
                return json.dumps({'status': 'ok'})
            else:
                return json.dumps({'status': 'error', 'error': ['Invalid password.']})
        else:
            return json.dumps({'status': 'error', 'error': ['User has an unknown password hash.']})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/register", methods=['POST'])
def do_register():
    form = RegistrationForm()
    if form.validate():
        # check if user or email are in use
        if User.query.filter_by(username=form.username.data).first():
            return json.dumps({'status': 'error', 'error': ['Username is already registered.']})
        if User.query.filter_by(email=form.email.data).first():
            return json.dumps({'status': 'error', 'error': ['Email is alredy in use.']})
        user = User(form.username.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})

if __name__ == "__main__":
    app.run()
