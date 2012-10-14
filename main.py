import logging
import webapp2
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os
import settings

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

default_key_sessions = db.Key.from_path('Session', 'default_session')
default_key_crashlog = db.Key.from_path('Crashlog','default_crashlog')

#Models:
class Session(db.Model):
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

#RequestHandlers:
class BaseHandler(webapp2.RequestHandler):
	isSuperAdmin = False

	def isUserSuperAdmin(self,user):
		return user.email() == settings.superadmin

	def isAuthorized(self):
		user = users.get_current_user()
		if (not user):
			self.authorize()
			return False
		if self.isUserSuperAdmin(user):
			self.isSuperAdmin = True
		else:
			userModel = User.gql("WHERE email = :1", db.Email(user.email())).get()
		return self.isSuperAdmin or (userModel and userModel.authorized)

	def authorize(self):
		self.redirect(users.create_login_url(self.request.uri))
	
	def renderTemplate(self,template_name,template_values):
		self.response.headers['Content-Type'] = 'text/html'
		template_values['logoutUrl']=users.create_logout_url("/")
		template_values['isAuthorized']=self.isAuthorized()
		template_values['isSuperAdmin']=self.isSuperAdmin
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(template_values))
	
class MainHandler(BaseHandler):	
	def get(self):
		template_values = {}
		self.renderTemplate('index.html',template_values)

class SessionHandler(BaseHandler):
	def post(self):
		data = json.loads(self.request.body)
		session = Session(default_key_sessions)
		session.name = data['name']
		session.token = data['token']
		session.put()
		self.response.out.write('Success')

class SessionsGetHandler(BaseHandler):
	def get(self):
		isAuthorized = self.isAuthorized()
		sessions = None
		if isAuthorized:
			sessions_query = Session.all().ancestor(default_key_sessions).order('-created')
			sessions = sessions_query.fetch(20)
			template_values = {
				'sessions': sessions,
	        }
			self.renderTemplate('sessions.html',template_values)

class CrashLogsGetHandler(BaseHandler):
	def get(self):
		if self.isAuthorized():
			key_value = self.request.get('id')
			if key_value:
				template_values = {
					'crashlog':Crashlog.get(key_value)
				}
				template = 'singlecrashlog.html'
			else:
				crashlogs_query = Crashlog.all().ancestor(default_key_crashlog).order('-created')
				crashlogs = crashlogs_query.fetch(20)
				cursor = crashlogs_query.cursor()
				template_values = {
					'cursor':cursor
					'crashlogs':crashlogs
				}
				template = 'crashlogs.html'
			self.renderTemplate(template,template_values)

class CrashLogHandler(BaseHandler):
	def post(self):
		data = json.loads(self.request.body)
		crashlog = Crashlog(default_key_crashlog)
		crashlog.build = data['build']
		crashlog.device = data['device']
		crashlog.user = data['user']
		crashlog.error = data['error']
		crashlog.crashlog = data['crashlog']
		crashlog.put()
		self.response.out.write('Success')

class UsersHandler(BaseHandler):
	def get(self):
		if self.isAuthorized() and self.isSuperAdmin:
			users = User.all().run()
			template_values = {
				'users':users,
				'superadmin':settings.superadmin
			}
			self.renderTemplate('users.html',template_values)
		else:
			self.redirect('/')

	def post(self):
		if self.isAuthorized() and self.isSuperAdmin:
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
				user = User(email=db.Email(email),authorized=True)
				user.put()
			self.redirect('/users')
		else:
			self.redirect('/') 

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
	('/sessions',SessionsGetHandler),
	('/crashlogs',CrashLogsGetHandler),
	('/crashlog.json',CrashLogHandler),
	('/session.json',SessionHandler),
	('/users',UsersHandler)
], debug=True)
