import cgi
import urllib
import webapp2
import jinja2
import os
import twilio.twiml
from google.appengine.api import channel
from model.Twilio_Info import *
from google.appengine.api import users
from google.appengine.ext import db
from twilio.rest import TwilioRestClient

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
		#self.redirect("/poll_sms_handler")
		self.redirect("/generate_number")
		
class Poll_Save(webapp2.RequestHandler):

	def post(self):
		#user_key = self.request.get('user_key_info')
		poll_info = Poll_Data()
		poll_info.question = cgi.escape(self.request.get('question'))
		poll_info.data = cgi.escape(str(self.request.get('dictionary')))
		poll_info.put()
		k = twilio_info1.key()  # key is complete, has ID
		id = k.id()  # the system-assigned ID
		self.response.out.write("""<br>""")
		self.response.out.write(id)
		self.redirect("/generate_number")
		
class Choose_Number(webapp2.RequestHandler):
	def post(self):
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.list()
		template_values = {
			'numbers' : numbers,
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
			
		}
		template = jinja_environment.get_template('choose_number.html')
		self.response.out.write(template.render(template_values))
		
		
class Generate_Number(webapp2.RequestHandler):
	def get(self):
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.search(type="local")
		#self.response.out.write("""<br>""")
		#Purchase the first number in the list
		if numbers:
			#print numbers[0].phone_number
			#self.response.out.write("hi")
			#self.response.out.write("""<br>""")
			#self.response.out.write("%s" %(numbers[0].phone_number))
			#self.response.out.write("""<br>""")
			#self.response.out.write(numbers[0].phone_number)
			numbers[0].purchase()
			#self.response.out.write(numbers[0])
			#generated_number = numbers[0]
		numbers = client.phone_numbers.list(phone_number="%s" %(numbers[0].phone_number))
		if numbers:
			number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply")
			#self.response.out.write(number.sms_url)
			#print number.sms_url
		self.redirect("/poll_sms_handler?number=" + "%s" %(numbers[0].phone_number))
		
class Auto_Reply_Sms(webapp2.RequestHandler):
	sender_number = 0
	# def get(self):
		# message = "Thank you for participating in the poll. Your vote has been recorded"
		# resp = twilio.twiml.Response()
		#print "hi-after resp"
		# resp.sms(message)
		# message1= str(resp)
		#webapp2.Response(message1)
		# self.response.write(message1)
		
	def post(self):
		message = "Thank you for participating in the poll. Your vote has been recorded"
		resp = twilio.twiml.Response()
		#print "hi"
		#print "%s" %(self.request.get('Body'))
		resp.sms(message)
		message1= str(resp)
		#webapp2.Response(message1)
		sender_number = self.request.get('From')	
		channel.send_message('1234', "%s" % (self.request.get('Body')))
		self.response.write(message1)
		#self.redirect("/poll_sms_handler")
		#self.response.out.write(message1)
		#self.response.out.write(self.request.get('Body'))
		
class Poll_Sms_Handler(webapp2.RequestHandler):
	def post(self):
		#phone = self.request.get('number')
		#client_id = os.urandom(16).encode('hex')
		channel_key = channel.create_channel('1234')
		template_values = {
			'phone_number': self.request.get('number'),
			'client_id': users.get_current_user().nickname(),
			'channel_key': channel_key,
			}
		template = jinja_environment.get_template('poll_start_new.html')
		self.response.out.write(template.render(template_values))
		
app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/profile', Profile), ('/save', Twilio_Save), ('/generate_number', Generate_Number), ('/auto_reply', Auto_Reply_Sms), ('/poll_sms_handler', Poll_Sms_Handler), ('/choose_number', Choose_Number)
], debug=True)
 