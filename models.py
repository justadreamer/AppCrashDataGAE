# -*- coding: utf-8 -*-

""" Models for GAE CrashLogs collector project.
"""
from google.appengine.ext import db
from settings import ROLE_USER, ROLE_ADMIN

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

class UserRole(db.Model):
    """ To get all users for some particulear role use following syntaxis:
        all_user_for_this_role = UserRole().user_set

        Another example:
        my_boy = UserRole().users.filter('name =', 'Darth Vader') # to filter users
        UserRole().users.filter('name =', 'Count Dooku').get().delete() # to delete 
    """
    name = db.StringProperty(required=True, default=ROLE_USER, choices=(ROLE_USER, ROLE_ADMIN))

class User(db.Model):
    email = db.EmailProperty(required=True)
    authorized = db.BooleanProperty(default=False, required=True)

    # a reference to a UserRole class
    # this forms one-to-many relationship between a UserRole and a User
    # (one UserRole - to - many User-s)
    role = db.ReferenceProperty(UserRole, collection_name='users')

