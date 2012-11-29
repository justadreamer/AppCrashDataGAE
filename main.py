# -*- coding: utf-8 -*-

import logging
import webapp2
from models import Session, Crashlog, User, UserRole, FallenApp
from utils.users import requiring, requiring_app_key
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os
import settings
from utils import helpers

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
	@requiring(settings.ROLE_USER)
	def get(self):
		template_values = {}
		self.renderTemplate('index.html',template_values)

class SessionHandler(BaseHandler):
	# TODO: create and place here sort of @id_required decorator
	def post(self):
		data = json.loads(self.request.body)
		session = Session()
		session.name = data['name']
		session.token = data['token']
		session.put()
		self.response.out.write('Success')

class SessionsGetHandler(BaseHandler):
	@requiring(settings.ROLE_USER)
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
	@requiring(settings.ROLE_USER)
	def get(self):
		key_value = self.request.get('id')
		if key_value:
			template_values = {
				'crashlog':Crashlog.get(key_value)
				}
			template = 'singlecrashlog.html'
		else:
			app_id_value = self.request.get('app_id')
			app = None
			if app_id_value:
				app = FallenApp.get(app_id_value)
			if app:
				crashlogs_query = Crashlog.all().ancestor(app).order('-created')
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
				'app_name': (lambda x: x.name if x else 'All applications')(app),
				}
			template = 'crashlogs.html'
		self.renderTemplate(template,template_values)

class CrashLogHandler(BaseHandler):
	@requiring_app_key
	def post(self, *args, **kwargs):
		parent = kwargs.get('app_entity', default=None)
		data = json.loads(self.request.body)
		crashlog = Crashlog(parent=parent)
		crashlog.build = data['build']
		crashlog.device = data['device']
		crashlog.user = data['user']
		crashlog.error = data['error']
		crashlog.crashlog = data['crashlog']
		crashlog.put()
		self.response.out.write('Success')

class UsersHandler(BaseHandler):
	@requiring(settings.APP_OWNER)
	def get(self):
		users = User.all().run()
		template_values = {
			'users':users,
			}
		self.renderTemplate('users.html',template_values)

	@requiring(settings.APP_OWNER)
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
					user.role = UserRole.all().filter("name =", settings.ROLE_USER).get()
				user.put()
		elif email:
			# create a new user
			user = User(email=db.Email(email), authorized=True,
					role=UserRole.all().filter("name =", settings.ROLE_USER).get())
			user.put()
		self.redirect('/users')

class ApplicationsHandler(BaseHandler):
	@requiring(settings.ROLE_USER)
	def get(self):
		apps = FallenApp.all().run()
		apps_list = [{'name':app.name, 'id':app.key()} for app in apps]
		self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
		self.response.out.write(json.dumps(apps_list))

class UsersMigrationHandler(BaseHandler):
	@requiring(settings.APP_OWNER)
	def get(self):
		# create UserRole objects in DB
		for role in (settings.ROLE_USER, settings.ROLE_ADMIN):
			helpers.create_role_if_doesnt_exist(role)
		# update users 
		report = []

		user_role = UserRole.all().filter("name =", settings.ROLE_USER).get()
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
			'report': [str(line) for line in report]}
		self.renderTemplate('message.html',template_values)

class CrashlogsMigrationHandler(BaseHandler):
	@requiring(settings.APP_OWNER)
	def get(self):
		# create DefaultApplication object in DB
		helpers.create_app_model_if_doesnt_exist(settings.DEFAULT_APP)
		default_app = FallenApp.all().filter("name =", settings.DEFAULT_APP).get()
		
		success_counter = 0 # number of successfully migrated crashlog entities
		failed_counter = 0 # same of failed to migrate
		need_to_be_migrated = 0 # number of entities are to be migrated
		total = 0 # overall number of crashlog entities in the DB

		crashlogs_query = Crashlog.all()
		for each in crashlogs_query.run():
			total += 1
			parent_model = each.parent()
			if not parent_model or parent_model.kind() != 'FallenApp':
				need_to_be_migrated += 1
				if helpers.copy_obj_with_changes(original=each, parent=default_app):
					success_counter += 1
				else:
					failed_counter += 1
		message = "Migration is finished"
		# # failed to get a UserRole instance
		# message = "User role: %s" % str(user_role)

		rep = ["migrated: %s, not migrated: %s," % (success_counter, failed_counter),
			   "were considered to be migrated: %s," %  need_to_be_migrated,
			   "total number of verified crashlogs: %s" % total,
			  ]

		template_values = {
			'message':message,
			'report': rep}
		self.renderTemplate('message.html',template_values)

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
	('/sessions', SessionsGetHandler),
	('/crashlogs', CrashLogsGetHandler),
	('/crashlog.json', CrashLogHandler),
	('/session.json', SessionHandler),
	('/users', UsersHandler),
	('/users/migration', UsersMigrationHandler),
	('/crashlogs/migration', CrashlogsMigrationHandler),
	('/applications', ApplicationsHandler),
], debug=settings.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
