import cgi
import urllib
import webapp2
import jinja2
import os
import json
import twilio.twiml
from google.appengine.api import channel
from model.Twilio_Info import *
from google.appengine.api import users
from google.appengine.ext import db
from twilio.rest import TwilioRestClient

#Global
data = dict()
option_data = dict()
incoming_poll_numbers = dict()
data_number = 1

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'view')))
	
class MainHandler(webapp2.RequestHandler):
    def get(self):
		user = users.get_current_user()
		data.clear()
		incoming_poll_numbers.clear()
		option_data.clear()
		global data_number
		data_number = 1
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
		
class Poll_Number(webapp2.RequestHandler):
    def post(self):
		data.clear()
		incoming_poll_numbers.clear()
		option_data.clear()
		global data_number
		data_number = 1
		template_values = {
		}
		template = jinja_environment.get_template('poll_number.html')
		self.response.out.write(template.render(template_values))		
		  
class Twilio_Save(webapp2.RequestHandler):
	def post(self):
		user_key = self.request.get('user_key_info')
		twilio_info1 = Twilio_Info(key_name='%s' % (users.get_current_user().nickname()))
		twilio_info1.twilio_username = cgi.escape(self.request.get('username'))
		twilio_info1.twilio_password = cgi.escape(self.request.get('password'))
		twilio_info1.twilio_url = cgi.escape(self.request.get('URL'))
		twilio_info1.put()
		self.redirect("/")
		#self.redirect("/generate_number")
		
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
		
class Add_Sms_URL(webapp2.RequestHandler):
	def post(self):
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.list(phone_number="%s" %(self.request.get('number')))		
		if numbers:
			number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply")
			self.redirect("/poll?number=" + "%s" %(number.phone_number))
		
class Generate_Number(webapp2.RequestHandler):
	def post(self):
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
		self.redirect("/poll?number=" + "%s" %(numbers[0].phone_number))
		
class Auto_Reply_Sms(webapp2.RequestHandler):
	sender_number = 0
	option_number = 0
	# def get(self):
		# message = "Thank you for participating in the poll. Your vote has been recorded"
		# resp = twilio.twiml.Response()
		#print "hi-after resp"
		# resp.sms(message)
		# message1= str(resp)
		#webapp2.Response(message1)
		# self.response.write(message1)
		
	def post(self):
		
		resp = twilio.twiml.Response()
		#print "hi"
		#print "%s" %(self.request.get('Body'))
		if((not(incoming_poll_numbers.has_key("%s" %(self.request.get('From')))))) :
			if (str(self.request.get('Body'))).isdigit() :
				option_number = int(self.request.get('Body'))
				if(len(data) < 1):
					message = "The poll has not yet started."
				if((incoming_poll_numbers.has_key("%s" %(self.request.get('From')))) and (len(data) > 0)):
					message = "Your vote has already been recorded."
				if((not(incoming_poll_numbers.has_key("%s" %(self.request.get('From'))))) and (len(data) < option_number) and (len(data) > 0)):
					message = "You have input an invalid option. Please vote again."
				if((not(incoming_poll_numbers.has_key("%s" %(self.request.get('From'))))) and (len(data) >= option_number) and (len(data) > 0)):
					incoming_poll_numbers["%s" %(self.request.get('From'))] = "%s" % (self.request.get('Body'))	
					channel.send_message('1234', "%s" % (self.request.get('Body')))
					message = "Thank You.Your vote has been recorded"
			else :
				message = "You have input an invalid option. Please vote again."
		else :
			message = "Your vote has already been recorded."
		resp.sms(message)
		message1= str(resp)
		#resp.sms(message1)
		#webapp2.Response(message1)
		sender_number = self.request.get('From')	
		#channel.send_message('1234', "%s" % (self.request.get('Body')))
		self.response.write(message1)
		#self.redirect("/poll_sms_handler")
		#self.response.out.write(message1)
		#self.response.out.write(self.request.get('Body'))
		
class Twilio_Poll(webapp2.RequestHandler):
#Initital Call to Poll Page	
	def post(self):
		#global data_number
		#data.clear()
		#incoming_poll_numbers.clear()
		#data_number = 1
		#option_data.clear()
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
            'question': self.request.get('question'),
			'number' : self.request.get('number')
		}
		template = jinja_environment.get_template('poll.html')
		self.response.out.write(template.render(template_values))

#Subsequent calls after the initial call to poll page
	def get(self):
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
            'question': self.request.get('question'),
			'data_store': json.dumps(data),
			'number' : self.request.get('number')
 		}
		template = jinja_environment.get_template('poll.html')
		self.response.out.write(template.render(template_values))	
		
		
class Option_Save(webapp2.RequestHandler):
	def post(self):
		global data_number
		question = self.request.get('question')
		options = self.request.get('options')
		number = self.request.get('number')
		data[options] = 0
		option_data[data_number] = options
		data_number = data_number + 1
		#self.response.out.write(data.keys())
		self.redirect('/poll?question=' + question + '&number=' + number)

class Start_Poll(webapp2.RequestHandler):	
	def post(self):			
		channel_key = channel.create_channel('1234')
 		template_values = {
		    'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
	        'question': self.request.get('question'),
			'data_store': json.dumps(data),
			'option_data': json.dumps(option_data),
			'phone_number': self.request.get('number'),
			'client_id': users.get_current_user().nickname(),
			'channel_key': channel_key,
		}
		template = jinja_environment.get_template('start_poll.html')
		self.response.out.write(template.render(template_values))

class Stop_Poll(webapp2.RequestHandler):		
	def post(self):
		#question = self.request.get('poll_question')
		#poll_data = self.request.get('polldata')
		
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		poll_number = int(self.request.get('poll_number'))
		numbers = client.phone_numbers.list(phone_number="%s%s" %('+', poll_number))		
		if numbers:
			number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="")
		for number in incoming_poll_numbers :
			message = client.sms.messages.create(body="%s%s" %("Thank you for visiting the demo. You can find me at- ", q.twilio_url), to='%s%s' % ('+', number), from_='%s%s' % ('+', poll_number))
		self.response.out.write(self.request.get('poll_question'))
		self.response.out.write(self.request.get('polldata'))
		poll_info = Poll_Data()
		poll_info.poll_question = cgi.escape(str(self.request.get('poll_question')))
		poll_info.poll_data = cgi.escape(str(self.request.get('polldata')))
		poll_info.user_name = '%s' % (users.get_current_user().nickname())
		poll_info.put()
		k = poll_info.key()  # key is complete, has ID
		id = k.id() 
		# self.response.out.write("The data is saved")
		self.redirect("/results/%d" % id)
		
		
class Permalink(webapp2.RequestHandler):
    def get(self, poll_id):
		key_list = []
		values_list = []
		poll_data_redirect = Poll_Data.get_by_id(int(poll_id))
		# eval(poll_data_redirect.poll_data)
		if((len(str(poll_data_redirect.poll_data))) > 0) :
			key_list = (eval(poll_data_redirect.poll_data)).keys()
			values_list = (eval(poll_data_redirect.poll_data)).values()
		template_values = {
			'poll_data_redirect': Poll_Data.get_by_id(int(poll_id)),
			'poll_id': poll_id,
			'options_list' : key_list,
			'votes_list' : values_list,
		}
        #poll_data_redirect = Poll_Data.get_by_id(int(poll_id))  json.dumps(poll_data_redirect.poll_data)
		template = jinja_environment.get_template('results.html')
		self.response.out.write(template.render(template_values))
        #self.render("results.html", poll_data_redirect = poll_data_redirect)
		
class Poll_History(webapp2.RequestHandler):	
	def post(self):			
		entity = Poll_Data.all()
		entity.filter("user_name =", "%s" % (users.get_current_user().nickname()))
		poll_history_data = entity.run()
 		template_values = {
		    'history_data': poll_history_data,
		}
		template = jinja_environment.get_template('poll_history.html')
		self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/profile', Profile), ('/save', Twilio_Save), ('/generate_number', Generate_Number), ('/auto_reply', Auto_Reply_Sms), ('/choose_number', Choose_Number), ('/poll_number', Poll_Number), ('/poll', Twilio_Poll), ('/option_save', Option_Save), ('/Start_Poll', Start_Poll), ('/add_sms_url', Add_Sms_URL), ('/stop_poll', Stop_Poll), ('/results/(\d+)', Permalink), ('/poll_history', Poll_History)
], debug=True)
 