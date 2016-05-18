#!/usr/bin/env python3
# -*- coding: utf-8

from flask import Flask, render_template, flash, request
from models import db, User
import config
import json
from forms import RegistrationForm

app = Flask(__name__)

app.config.from_object(config)

db.init_app(app)

@app.before_first_request
def initialize_database():
    db.create_all()


@app.route("/")
def index():
    register = RegistrationForm()
    return render_template('index.html', regform=register)

def get_errors(form):
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret

@app.route("/test/register")
def test_register():
    form = RegistrationForm()
    return render_template('test.html', form=form)

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
