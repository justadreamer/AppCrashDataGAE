# -*- coding: utf-8 -*-


from google.appengine.api import users
from google.appengine.ext import db
from models import User, UserRole
from settings import ROLE_USER, ROLE_ADMIN


def requiring(required_role):
    """A decorator (actually it's a creator of a decorator) which takes arguments like 
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
            
            self.isSuperAdmin = users.is_current_user_admin()
            if required_role == 'app_owner':
                if not self.isSuperAdmin:
                    if self.request.method != 'GET':
                        self.abort(403, detail='You don\'t have access to this resource. Log in as admin!')
                    return self.redirect('/')
                else:
                    handler_method(self, *args, **kwargs)

            elif required_role not in (ROLE_USER, ROLE_ADMIN):
                self.abort(406, detail='Wrong user role: %s' % required_role)
            
            # the rest of variants are ROLE_USER or ROLE_ADMIN
            else:
                # if user is authanticated - check permissions to access our content
                # (user can be authanticated because GAE easily gives access to all google users)
                user_in_my_list = User.all().filter("email =",db.Email(user.email())).get()
                # user presents in our DB, has appropriate role and property authorized is TRUE 
                # (an application owner can switch it on/off)
                if user_in_my_list and user_in_my_list.authorized:
                    if (required_role == user_in_my_list.role.name) or \
                       (required_role == ROLE_USER and user_in_my_list.role.name in (ROLE_ADMIN, ROLE_USER)): # 1st check is for admin
                        handler_method(self, *args, **kwargs)
                else:                
                    if self.request.method != 'GET':
                        self.abort(403, detail='You don\'t have access to this resource.')
                    self.renderTemplate('unauthorized.html',{})

        return role_checker
    return dcrtr_itself