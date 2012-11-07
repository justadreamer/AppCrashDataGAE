# -*- coding: utf-8 -*-


from google.appengine.api import users
from google.appengine.ext import db
from models import User
import settings

def login_required(handler_method):
    """A decorator which checks if a user is logged in and 
        authorized (allowed to see the content).

        To use it, decorate your get() or post () method like this::

            @login_required
            def get(self):
                user = users.get_current_user(self)
                self.response.out.write('Hello, ' + user.nickname())

    """
    def check_login(self, *args, **kwargs):
        user = users.get_current_user()
        if not user:
            if self.request.method != 'GET':
                # if request is POST it's better not to redirect to the link an unauthorized 
                # user tried to post
                self.abort(403, detail='You don\'t have access to this resource. Log in first!')
            return self.redirect(users.create_login_url(self.request.url))
        else:
            # if user is authanticated - check permissions to access our content
            # (user can be authanticated because GAE easily gives access to all google users)
            userModel = User.all().filter("email =",db.Email(user.email())).get()
            # user presents in our DB and property authorized is TRUE (superAdmin can switch it on/off)
            if userModel and userModel.authorized:
                self.isAuthorized = True
                handler_method(self, *args, **kwargs)
            else:
                self.renderTemplate('index.html',{})

    return check_login


def super_admin_required(handler_method):
    """A decorator to require that a user be an Superadmin for this application
        to access a handler.

        To use it, decorate your get()/post() method like this::

            @super_admin_required
            def get(self):
                user = users.get_current_user(self)
                self.response.out.write('Hello, ' + user.nickname())

        We will redirect to a login page if the user is not logged in.
    """
    def check_s_admin(self, *args, **kwargs):
        user = users.get_current_user()
        if not user:
            if self.request.method != 'GET':
                self.abort(403, detail='You don\'t have access to this resource. Log in first!')
            return self.redirect(users.create_login_url(self.request.url))
        elif not user.email() == settings.superadmin:
            self.abort(403, detail='You don\'t have access to this resource.')
        else:
            handler_method(self, *args, **kwargs)

    return check_s_admin

def admin_required(handler_method):
    """A decorator to require that a user be an admin for this application
        to access a handler.

        To use it, decorate your get()/post() method like this::

            @admin_required
            def get(self):
                user = users.get_current_user(self)
                self.response.out.write('Hello, ' + user.nickname())

        We will redirect to a login page if the user is not logged in. 
    """
    def check_admin(self, *args, **kwargs):
        user = users.get_current_user()
        if not user:
            if self.request.method != 'GET':
                self.abort(403, detail='You don\'t have access to this resource. Log in first!')
            return self.redirect(users.create_login_url(self.request.url))
        elif not users.is_current_user_admin():
            if self.request.method != 'GET':
                self.abort(403, detail='You don\'t have access to this resource. Log in as admin!')
            return self.redirect('/')
        else:
            handler_method(self, *args, **kwargs)

    return check_admin



# this decorator was provided to replace three ones above
def requiring(required_role):
    """A decorator (actually it's a decorator creator) which takes arguments like 
        'user', 'admin' and 'app_owner' and require that a user: to be logged in and 
        uathorized, to be logged in and given extra permissions, to be logged in and 
        an admin for this application - correspondingly, to access a handler. 

        To use it, decorate your get()/post() method like this::

            @requiring('user')
            def get(self):
                user = users.get_current_user(self)
                self.response.out.write('Hello, ' + user.nickname())
    """
    def dcrtr_itself(handler_method):
        def role_checker(self, *args, **kwargs):
            user = users.get_current_user()
            if not user:
                if self.request.method != 'GET':
                    self.abort(403, detail='You don\'t have access to this resource. Log in first!')
                return self.redirect(users.create_login_url(self.request.url))
            if required_role == 'user':
                # if user is authanticated - check permissions to access our content
                # (user can be authanticated because GAE easily gives access to all google users)
                user_in_my_list = User.all().filter("email =",db.Email(user.email())).get()
                # user presents in our DB and property authorized is TRUE (an application owner 
                # can switch it on/off)
                if user_in_my_list and user_in_my_list.authorized:
                    handler_method(self, *args, **kwargs)
                else:
                    if self.request.method != 'GET':
                        self.abort(403, detail='You don\'t have access to this resource.')
                    self.renderTemplate('unauthorized.html',{})
            elif required_role == 'admin':
                # This part is about a user with extra permissions
                # which are given him by an application owner.
                # Can be reworked and made as part of user authorization
                # procedure above 
                if not user.email() == settings.superadmin:
                    self.abort(403, detail='You don\'t have access to this resource.')
                else:
                    handler_method(self, *args, **kwargs)
            elif required_role == 'app_owner':
                if not users.is_current_user_admin():
                    if self.request.method != 'GET':
                        self.abort(403, detail='You don\'t have access to this resource. Log in as admin!')
                    return self.redirect('/')
                else:
                    handler_method(self, *args, **kwargs)
            else:
                self.abort(406, detail='Wrong user role: %s' % required_role)

        return role_checker
    return dcrtr_itself