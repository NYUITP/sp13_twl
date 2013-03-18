

import cgi
import urllib
import webapp2
import jinja2
import os
import json


from model.Twilio_Info import *
from google.appengine.api import users
from google.appengine.ext import db

#Global
data = dict()


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'view')))
	
class MainHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
			template_values = {
            'name': user.nickname(),
            'url': users.create_logout_url("/"),
			}
			template = jinja_environment.get_template('index.html')
			self.response.out.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))
			
class Profile(webapp2.RequestHandler):
    def post(self):
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
		}
		template = jinja_environment.get_template('profile.html')
		self.response.out.write(template.render(template_values))
		  
class Twilio_Save(webapp2.RequestHandler):
	def post(self):
		user_key = self.request.get('user_key_info')
		twilio_info1 = Twilio_Info(key_name='%s' % (users.get_current_user().nickname()))
		twilio_info1.twilio_username = cgi.escape(self.request.get('username'))
		twilio_info1.twilio_password = cgi.escape(self.request.get('password'))
		twilio_info1.put()
		
class Twilio_Poll(webapp2.RequestHandler):
#Initital Call to Poll Page	
	def post(self):
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
            'question': self.request.get('question')

		}
		template = jinja_environment.get_template('poll.html')
		self.response.out.write(template.render(template_values))

#Subsequent calls after the initial call to poll page
	def get(self):
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
            'question': self.request.get('question')
 
		}
		template = jinja_environment.get_template('poll.html')
		self.response.out.write(template.render(template_values))	
		
		
class Option_Save(webapp2.RequestHandler):	

	def post(self):
		question = self.request.get('question')
		options = self.request.get('options')
		data[options] = 0
		#self.response.out.write(data.keys())
		self.redirect('/poll?' + urllib.urlencode({'question': question}))

	

class Start_Poll(webapp2.RequestHandler):	
			def post(self):	
				#data_store = []
				#data_store = 
  
 				template_values = {
		            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
		            'question': self.request.get('question'),
	            	'data_store': json.dumps(data)
					#'data_store': self.request.get('data'),
				}

				template = jinja_environment.get_template('start_poll.html')
				self.response.out.write(template.render(template_values))
				
							
app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/profile', Profile), ('/save', Twilio_Save), ('/poll',Twilio_Poll), ('/option_save',Option_Save), ('/Start_Poll',Start_Poll)
], debug=True)
 