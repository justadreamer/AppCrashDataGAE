# -*- coding: utf-8 -*-

import logging
import webapp2
from models import Session, Crashlog, User, UserRole
from utils import requiring
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os
from settings import ROLE_USER, ROLE_ADMIN

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))


#RequestHandlers:


class BaseHandler(webapp2.RequestHandler):

	def __init__(self, *args, **kwargs):
		# call the ancestor class's __init__()
		super(BaseHandler, self).__init__(*args, **kwargs)
		self.isSuperAdmin = False
		self.perPage = 50

	def renderTemplate(self,template_name,template_values):
		self.response.headers['Content-Type'] = 'text/html; charset=iso-8859-1'
		template_values['logoutUrl']=users.create_logout_url("/")
		template_values['isSuperAdmin']=self.isSuperAdmin
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(template_values))
	
class MainHandler(BaseHandler):
	@requiring(ROLE_USER)
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
	@requiring(ROLE_USER)
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
	@requiring(ROLE_USER)
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
			# edit the user with provided key
			user = User.get(key)
			if self.request.get('delete'):
				user.delete()
			elif self.request.get('switch_auth'):
				user.authorized = not user.authorized
				user.put()
			elif self.request.get('switch_role'):
				if user.role:
					roles = UserRole.all().fetch(limit=2)
					new_role = lambda x: roles[0] if roles[0].name != x.name else roles[1]
					user.role = new_role(user.role)
				else:
					user.role = UserRole.all().filter("name =", ROLE_USER).get()
				user.put()
		elif email:
			# create a new user
			user = User(email=db.Email(email), authorized=True,
					role=UserRole.all().filter("name =", ROLE_USER).get())
			user.put()
		self.redirect('/users')

def create_role(role_name):
	if not UserRole.all().filter("name =", role_name).get():
		UserRole(name=role_name).put()

class MigrationHandler(BaseHandler):
	@requiring('app_owner')
	def get(self):
		# create UserRole objects in DB
		for role in (ROLE_USER, ROLE_ADMIN):
			create_role(role)
		# update users 
		report = []

		user_role = UserRole.all().filter("name =", ROLE_USER).get()
		if user_role:
			for each in User.all().run():
				if each.role is None:
					each.role = user_role
					report.append({'user': each.email, 'role.name': user_role.name, 'user.role.name': each.role.name}) # 
					each.put() 
			message = "Migration is finished"
		else:
			# failed to get a UserRole instance
			message = "User role: %s" % str(user_role)

		template_values = {
			'message':message,
			'report': str(report)}
		self.renderTemplate('message.html',template_values)

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
	('/sessions', SessionsGetHandler),
	('/crashlogs', CrashLogsGetHandler),
	('/crashlog.json', CrashLogHandler),
	('/session.json', SessionHandler),
	# ('/migration', MigrationHandler),
	('/users', UsersHandler),
	('/users/migration', MigrationHandler),
], debug=True)
logging.getLogger().setLevel(logging.DEBUG)
