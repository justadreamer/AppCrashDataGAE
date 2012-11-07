# -*- coding: utf-8 -*-
""" Models for GAE CrashLogs collector project.
"""
from google.appengine.ext import db

class Session(db.Model):
    """A session of a user of a mobile application which sends us a crashlog"""
    name = db.StringProperty()
    token = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

class Crashlog(db.Model):
    build = db.StringProperty()
    device = db.StringProperty()
    user = db.StringProperty()
    error = db.StringProperty()
    crashlog = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add=True)

class User(db.Model):
    email = db.EmailProperty()
    authorized = db.BooleanProperty()
