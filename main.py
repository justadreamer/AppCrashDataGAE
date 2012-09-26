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
import webapp2
import json
from google.appengine.api import users
from google.appengine.ext import db
import jinja2
import os

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class Session(db.Model):
	name = db.StringProperty()
	token = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)

default_key = db.Key.from_path('Session', 'default_session')

class MainHandler(webapp2.RequestHandler):
	def isAuthorized(self,user):
		authorized = ['eugene.dorfman@gmail.com','eugene.dorfman@postindustria.com','alexander.antonyuk@postindustria.com']
		return user and user.email() in authorized

	def get(self):
		user = users.get_current_user()

		if user:
			self.response.headers['Content-Type'] = 'text/html'
			isAuthorized = self.isAuthorized(user)
			sessions = None
			if isAuthorized:
				sessions_query = Session.all().ancestor(default_key).order('-created')
				sessions = sessions_query.fetch(10)

			template_values = {
				'isAuthorized': isAuthorized,
				'sessions': sessions,
				'logoutUrl': users.create_logout_url("/")
	        }

			template = jinja_environment.get_template('index.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))

class SessionHandler(webapp2.RequestHandler):
	def post(self):
		data = json.loads(self.request.body)
		session = Session(default_key)
		session.name = data['name']
		session.token = data['token']
		session.put()
		self.response.out.write('Success')

app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/session.json',SessionHandler)
], debug=True)
