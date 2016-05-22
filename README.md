# throat

## Dependencies:

| Dependencies  | huh           |
| ------------- | ------------- |
| gunicorn      | Gunicorn 'Green Unicorn' is a Python WSGI HTTP Server for UNIX |
| flask | A lightweight Python web framework |
| flask-wtf | Offers simple integration with WTForms |
| flask-assets | Helps to integrate webassets into your Flask application |
| sqlalchemy | Python SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL |
| flask-sqlalchemy | An extension for Flask that adds support for SQLAlchemy to your application |
| bcrypt | Password hashing function|
| webassets | Asset management application for Python |
| jsmin | Removes comments and unnecessary whitespace from JavaScript files |
| cssmin | Removes comments and unnecessary whitespace from CSS files |

##Run local

from ubuntu 16.04

 - $ apt-get update
 - $ apt-get install git python-pip python3-pip libssl-dev libffi-dev python-dev python3-dev
 - $ pip3 install --upgrade pip

clone and install 

 - $ git clone https://github.com/Polsaker/throat.git
 - $ cd throat
 - $ pip3 install -r requirements.txt

run

 - $ python3 throat.py
