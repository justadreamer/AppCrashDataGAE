#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import webapp2
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os

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
	
#RequestHandlers:
class BaseHandler(webapp2.RequestHandler):
	def isAuthorized(self):
		logging.debug('called isAuthorized')
		user = users.get_current_user()
		if (not user):
			self.authorize()
			logging.debug('after call to authorize')	
			return False

		authorized = [
			'eugene.dorfman@gmail.com',
			'eugene.dorfman@postindustria.com',
			'alexander.antonyuk@postindustria.com',
			'oleg.kovtun@postindustria.com',
			'millena.korneeva@postindustria.com',
			'andrew.denisov@postindustria.com'
			'stanislav.baranov@postindustria.com',
			'vasiliy.dorozhinskiy@postindustria.com',
			]
		return user and user.email() in authorized

	def authorize(self):
		logging.debug('called authorize')
		self.redirect(users.create_login_url(self.request.uri))
	
	def renderTemplate(self,template_name,template_values):
		self.response.headers['Content-Type'] = 'text/html'
		template_values['logoutUrl']=users.create_logout_url("/")
		template_values['isAuthorized']=self.isAuthorized()
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(template_values))
	
class MainHandler(BaseHandler):	
	def get(self):
		logging.debug('before self.isAuthorized')
		isAuthorized = self.isAuthorized()
		template_values={
			'isAuthorized':isAuthorized
		};
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
				template_values = {
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

logging.getLogger().setLevel(logging.DEBUG)
app = webapp2.WSGIApplication([
    ('/', MainHandler), 
	('/sessions',SessionsGetHandler),
	('/crashlogs',CrashLogsGetHandler),
	('/crashlog.json',CrashLogHandler),
	('/session.json',SessionHandler)
], debug=True)