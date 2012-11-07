# -*- coding: utf-8 -*-

import logging
import webapp2
from models import Session, Crashlog, User
from utils import login_required, admin_required, requiring
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os
import settings

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))


#RequestHandlers:


class BaseHandler(webapp2.RequestHandler):

	def __init__(self, *args, **kwargs):
		# call the ancestor class's __init__()
		super(BaseHandler, self).__init__(*args, **kwargs)
		# if leave these attributes above then they will be shared among
		# all instances of this class. Not crucial but not good either
		# self.isAuthorized = False
		self.isSuperAdmin = False
		self.perPage = 50

	def isUserSuperAdmin(self, user):
		return user.email() == settings.superadmin

# USE! @login_required and @admin_required decorators enstead 
# of methods bellow

	# def isAuthorized(self):
	# 	user = users.get_current_user()
	# 	if (not user):
	# 		self.authorize()
	# 		return False
	# 	if self.isUserSuperAdmin(user):
	# 		self.isSuperAdmin = True
	# 	else:
	# 		userModel = User.gql("WHERE email = :1", db.Email(user.email())).get()
	# 	return self.isSuperAdmin or (userModel and userModel.authorized)

	# def authorize(self):
	# 	self.redirect(users.create_login_url(self.request.uri))
	
	def renderTemplate(self,template_name,template_values):
		self.response.headers['Content-Type'] = 'text/html; charset=iso-8859-1'
		template_values['logoutUrl']=users.create_logout_url("/")
		template_values['isSuperAdmin']=self.isSuperAdmin
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(template_values))
	
class MainHandler(BaseHandler):
	@requiring('user')
	def get(self):
		template_values = {}
		self.renderTemplate('index.html',template_values)

class SessionHandler(BaseHandler):
	# TODO: create and place here @id_required decorator
	def post(self):
		data = json.loads(self.request.body)
		session = Session()
		session.name = data['name']
		session.token = data['token']
		session.put()
		self.response.out.write('Success')

class SessionsGetHandler(BaseHandler):
	@requiring('user')
	def get(self):
		sessions = None
		sessions_query = Session.all().order('-created')
		cursor = self.request.get('cursor')
		if cursor:
			sessions_query = sessions_query.with_cursor(cursor)
			cursor = None
		sessions = sessions_query.fetch(self.perPage)
		if (len(sessions)==self.perPage):
			cursor = sessions_query.cursor()
		template_values = {
			'cursor':cursor,
			'sessions': sessions,
        }
		self.renderTemplate('sessions.html',template_values)

class CrashLogsGetHandler(BaseHandler):
	@requiring('user')
	def get(self):
		key_value = self.request.get('id')
		if key_value:
			template_values = {
				'crashlog':Crashlog.get(key_value)
			}
			template = 'singlecrashlog.html'
		else:
			crashlogs_query = Crashlog.all().order('-created')
			cursor = self.request.get('cursor')
			if cursor:
				crashlogs_query = crashlogs_query.with_cursor(cursor)
				cursor = None
			crashlogs = crashlogs_query.fetch(self.perPage)
			if len(crashlogs)==self.perPage:
				cursor = crashlogs_query.cursor()
			template_values = {
				'cursor' : cursor,
				'crashlogs':crashlogs,
			}
			template = 'crashlogs.html'
		self.renderTemplate(template,template_values)

class CrashLogHandler(BaseHandler):
	# TODO: create and place here @id_required decorator
	def post(self):
		data = json.loads(self.request.body)
		crashlog = Crashlog()
		crashlog.build = data['build']
		crashlog.device = data['device']
		crashlog.user = data['user']
		crashlog.error = data['error']
		crashlog.crashlog = data['crashlog']
		crashlog.put()
		self.response.out.write('Success')

class UsersHandler(BaseHandler):
	@requiring('app_owner')
	def get(self):
		users = User.all().run()
		template_values = {
			'users':users,
			}
		self.renderTemplate('users.html',template_values)

	@requiring('app_owner')
	def post(self):
		key = self.request.get('id')
		email = self.request.get('email')
		if key:
			user = User.get(key)
			if self.request.get('delete'):
				user.delete()
			elif self.request.get('switch'):
				user.authorized = not user.authorized
				user.put()
		elif email:
			user = User(email=db.Email(email), authorized=True)
			user.put()
		self.redirect('/users')

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
	('/sessions',SessionsGetHandler),
	('/crashlogs',CrashLogsGetHandler),
	('/crashlog.json',CrashLogHandler),
	('/session.json',SessionHandler),
	('/users',UsersHandler)
], debug=True)
logging.getLogger().setLevel(logging.DEBUG)
