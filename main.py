import cgi
import urllib
import webapp2
import jinja2
import os
import json
import random
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
incoming_raffle_numbers = dict()
data_number = 1
# Feature is 1 for Poll, 2 for Raffle
feature = 1
raffle_number = 0
poll_number = 0
question = ''
poll_id = 0

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'view')))

# Index Page (Controller)	
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
			
# Profile Page
# Set User Profile by adding TWILIO Credentials (Account SID, Authentication Code) and Evangelist URL(Displayed at the End of the POLL)	
class Profile(webapp2.RequestHandler):
    def get(self):
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
			'url': users.create_logout_url("/"),	
		}
		template = jinja_environment.get_template('profile.html')
		self.response.out.write(template.render(template_values))
		
# Allows User to Generate New Local Number or Select an prepurchased Existing Number from the database
class Poll_Number(webapp2.RequestHandler):
    def post(self):
		global feature
		task = str(self.request.get('activity'))
		if(task == 'Poll'):
			feature = 1
		if(task == 'Raffle'):
			feature = 2			
		data.clear()
		incoming_poll_numbers.clear()
		option_data.clear()
		global data_number
		data_number = 1
		template_values = {
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('poll_number.html')
		self.response.out.write(template.render(template_values))		
		  
# Save the Twilio Credentials from the Profile Page into the Database
class Twilio_Save(webapp2.RequestHandler):
	def post(self):
		user_key = self.request.get('user_key_info')
		twilio_info1 = Twilio_Info(key_name='%s' % (users.get_current_user().nickname()))
		twilio_info1.twilio_username = cgi.escape(self.request.get('username'))
		twilio_info1.twilio_password = cgi.escape(self.request.get('password'))
		twilio_info1.twilio_url = cgi.escape(self.request.get('URL'))
		twilio_info1.put()
		self.redirect("/")
		
# Select from a list of prepurchased Existing Numbers from the database to conduct poll/Raffle
class Choose_Number(webapp2.RequestHandler):
	def post(self):
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.list()
		template_values = {
			'numbers' : numbers,
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),	
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('choose_number.html')
		self.response.out.write(template.render(template_values))

# Configure Twilio Number to send SMS to Google App Engine
class Add_Sms_URL(webapp2.RequestHandler):
	def post(self):
		
		global raffle_number
		global feature
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.list(phone_number="%s" %(self.request.get('number')))		
		if numbers:
			if(feature == 1) :
				number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply")
				self.redirect("/poll?number=" + "%s" %(number.phone_number))
			if(feature == 2) :
			
				number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply_raffle")
				raffle_number = number.phone_number
				self.redirect("/Start_Raffle?number=" + "%s" %(number.phone_number))

# Purchase a new number to conduct poll/raffle		
class Generate_Number(webapp2.RequestHandler):
	def post(self):
		global raffle_number
		global feature
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		numbers = client.phone_numbers.search(type="local")

		#Purchase the first number in the list
		if numbers:
			numbers[0].purchase()
		numbers = client.phone_numbers.list(phone_number="%s" %(numbers[0].phone_number))
		if numbers:
			if(feature == 1) :
				number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply")
				self.redirect("/poll?number=" + "%s" %(numbers[0].phone_number))
			if(feature == 2) :
				number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="http://sp13-twilio.appspot.com/auto_reply_raffle")
				raffle_number = number.phone_number
				self.redirect("/Start_Raffle?number=" + "%s" %(numbers[0].phone_number))		

# Sends Automated text message on receipt of user sms		
class Auto_Reply_Sms(webapp2.RequestHandler):
	sender_number = 0
	option_number = 0
		
	def post(self):
		incoming_data_poll = []
		resp = twilio.twiml.Response()
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
					incoming_data_poll.append("%s" % (self.request.get('Body')))
					incoming_data_poll.append("onSms")
					channel.send_message('Poll', "%s" % (json.dumps(incoming_data_poll)))
					channel.send_message('Poll_User', "%s" % (json.dumps(incoming_data_poll)))
					message = "Thank You.Your vote has been recorded"
			else :
				message = "You have input an invalid option. Please vote again."
		else :
			message = "Your vote has already been recorded."
		resp.sms(message)
		message1= str(resp)
		sender_number = self.request.get('From')	
		del incoming_data_poll[0:len(incoming_data_poll)]
		self.response.write(message1)
		
# Sends Automated text message on receipt of user sms	
class Auto_Reply_Sms_Raffle(webapp2.RequestHandler):	
	def post(self):
		global incoming_raffle_numbers
		incoming_data = []
		resp = twilio.twiml.Response()
		if((not(incoming_raffle_numbers.has_key("%s" %(self.request.get('From')))))) :
			incoming_raffle_numbers["%s" %(self.request.get('From'))] = "%s" % (self.request.get('Body'))
			incoming_data.append("%s" % (self.request.get('Body')))
			incoming_data.append("%s" % (self.request.get('From')))
			incoming_data.append("onSms")
			channel.send_message('Raffle', "%s" % (json.dumps(incoming_data)))
			channel.send_message('Raffle_User', "%s" % (json.dumps(incoming_data)))
			message = "Thank You %s.Your are registered for the Raffle" % (str(self.request.get('Body')))
		else :
			message = "You have already participated in the Raffle"
		resp.sms(message)
		message1= str(resp)
		self.response.write(message1)	

# Initiate Twilio Poll - Evangelist Enters Poll Question and Options 		
class Twilio_Poll(webapp2.RequestHandler):
	def get(self):
		global question
		global poll_number
		question = str(self.request.get('question'))
		poll_number = int(self.request.get('number'))
		template_values = {
            'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
            'question': self.request.get('question'),
			'data_store': json.dumps(data),
			'number' : self.request.get('number'),
			'user_nickname' : users.get_current_user().nickname(),
			'url': users.create_logout_url("/"),
 		}
		template = jinja_environment.get_template('poll.html')
		self.response.out.write(template.render(template_values))	
		
# The Poll Data i.e. Question, Options and SMS Number is stored in the instance Variables
class Option_Save(webapp2.RequestHandler):
	def post(self):
		global data_number
		question = self.request.get('question')
		options = self.request.get('options')
		number = self.request.get('number')
		if(not(data.has_key("%s" % (options)))) :
			data[options] = 0
			option_data[data_number] = options
			data_number = data_number + 1
		self.redirect('/poll?question=' + question + '&number=' + number)

# The Poll iS started. The question, options and SMS Number is displayed on UI
class Start_Poll(webapp2.RequestHandler):	
	def post(self):
		poll =[]
		poll.append(1)	
		poll.append("onStart")	
		channel_key = channel.create_channel('Poll')
		channel.send_message('Poll_User', "%s" % (json.dumps(poll)))
 		template_values = {
		    'key': urllib.urlencode({'user_key_info': users.get_current_user().nickname()}),
	        'question': self.request.get('question'),
			'data_store': json.dumps(data),
			'option_data': json.dumps(option_data),
			'phone_number': self.request.get('number'),
			'client_id': users.get_current_user().nickname(),
			'channel_key': channel_key,
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('start_poll.html')
		self.response.out.write(template.render(template_values))

# User Page for Poll - Will Display the Number to the user / and Also live poll results		
class Start_Poll_User(webapp2.RequestHandler):	
	def get(self,name):
		global poll_number
		global question
		channel_key = channel.create_channel('Poll_User')
 		template_values = {
	        'question': str(question),
			'data_store': json.dumps(data),
			'option_data': json.dumps(option_data),
			'phone_number': poll_number,
			'channel_key': channel_key,
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('start_poll_user.html')
		self.response.out.write(template.render(template_values))

# The Poll is Terminated and Results are Displayed 
class Stop_Poll(webapp2.RequestHandler):		
	def post(self):
		data_poll = []
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		poll_number = int(self.request.get('poll_number'))
		numbers = client.phone_numbers.list(phone_number="%s%s" %('+', poll_number))		
		if numbers:
			number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="")
		for number in incoming_poll_numbers :
			message = client.sms.messages.create(body="%s%s" %("Thank you for visiting the demo. You can find me at- ", q.twilio_url), to='%s%s' % ('+', number), from_='%s%s' % ('+', poll_number))
		poll_info = Poll_Data()
		poll_info.poll_question = cgi.escape(str(self.request.get('poll_question')))
		if(len(str(self.request.get('polldata'))) > 1) :
			data_values = eval((str(self.request.get('polldata'))))
			global data
			global poll_number
			i = 0
			for item in data :
				data[option_data[i+1]] = data_values[i]
				i = i + 1
		poll_info.poll_data = (str(json.dumps(data)))
		poll_info.user_name = '%s' % (users.get_current_user().nickname())
		poll_info.put()
		k = poll_info.key()  # key is complete, has ID
		id = k.id() 
		data_poll.append("%s" % (id))
		data_poll.append("onFinish")
		channel.send_message('Poll_User', "%s" % (json.dumps(data_poll)))
		poll_number = 0
		del data_poll[0:len(data_poll)]
		self.redirect("/results/%d" % id)

# Generate Permalink for Poll Results		
class Permalink(webapp2.RequestHandler):
    def get(self, poll_id):
		key_list = []
		values_list = []
		poll_data_redirect = Poll_Data.get_by_id(int(poll_id))
		if((len(str(poll_data_redirect.poll_data))) > 0) :
			key_list = (eval(poll_data_redirect.poll_data)).keys()
			values_list = (eval(poll_data_redirect.poll_data)).values()
		template_values = {
			'poll_data_redirect': Poll_Data.get_by_id(int(poll_id)),
			'poll_id': poll_id,
			'options_list' : key_list,
			'votes_list' : values_list,
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('results.html')
		self.response.out.write(template.render(template_values))

# Displays the Poll History with a List of Previously Conducted Polls. 		
class Poll_History(webapp2.RequestHandler):	
	def get(self):			
		entity = Poll_Data.all()
		entity.filter("user_name =", "%s" % (users.get_current_user().nickname()))
		poll_history_data = entity.run()
 		template_values = {
		    'history_data': poll_history_data,
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('poll_history.html')
		self.response.out.write(template.render(template_values))

# Allows Evangelist to Delete old Polls		
class Delete_Poll(webapp2.RequestHandler):	
	def get(self, poll_id):		
		poll = Poll_Data.get_by_id(int(poll_id))
		poll.delete()
		self.redirect("/poll_history")

# Begin Raffle, It allows to Add NewEntry on the Fly
class Start_Raffle(webapp2.RequestHandler):	
	def get(self):
		raffle_data = []
		raffle_data.append(1)
		raffle_data.append(2)
		raffle_data.append("onStart")
		channel.send_message('Raffle_User', "%s" % (json.dumps(raffle_data)))
		channel_key = channel.create_channel('Raffle')
 		template_values = {
			'phone_number': self.request.get('number'),
			'channel_key': channel_key,
			'url': users.create_logout_url("/"),
			'user_nickname' : users.get_current_user().nickname(),
		}
		template = jinja_environment.get_template('start_raffle.html')
		self.response.out.write(template.render(template_values))

# Begin User Display page for Raffle to Display Raffle Participants and Results after the Raffle is Stopped		
class Start_Raffle_User(webapp2.RequestHandler):	
	def get(self,name):	
		global raffle_number
		channel_key = channel.create_channel('Raffle_User')
 		template_values = {
			'phone_number': raffle_number,
			'channel_key': channel_key,
			'url': users.create_logout_url("/"),
		}
		template = jinja_environment.get_template('start_raffle_user.html')
		self.response.out.write(template.render(template_values))

# Update the Page after the user is dynamically added/Removed
class Update_User_Raffle_Page(webapp2.RequestHandler):	
	def get(self):
		global incoming_raffle_numbers
		index = int(self.request.get('index'))
		i=0
		for key in incoming_raffle_numbers.iterkeys() :
			if(i == index):
				incoming_raffle_numbers.pop(key, None)
			i = i + 1	
		incoming_data_user = []
		
		incoming_data_user.append(1)
		incoming_data_user.append(2)
		incoming_data_user.append("onDelete")
		incoming_data_user.append("%s" % (index))
		channel.send_message('Raffle', "%s" % (json.dumps(incoming_data_user)))
		channel.send_message('Raffle_User', "%s" % (json.dumps(incoming_data_user)))
		del incoming_data_user[0:len(incoming_data_user)]
		
# Stop Raffle and Declare Result		
class Stop_Raffle(webapp2.RequestHandler):	
	def get(self):
		global incoming_raffle_numbers
		global raffle_number
		incoming_data_user = []
		q = Twilio_Info.get_by_key_name("%s" % (users.get_current_user().nickname()))
		client = TwilioRestClient(q.twilio_username, q.twilio_password)
		raffle_number = int(self.request.get('raffle_number'))
		numbers = client.phone_numbers.list(phone_number="%s%s" %('+', raffle_number))		
		if numbers:
			number = client.phone_numbers.update("%s" %(numbers[0].sid), sms_url="")	
		names = eval(str(self.request.get('raffle_names')))
		numbers_raffle = eval(str(self.request.get('raffle_incoming_numbers')))
		raffle_winner_name = str(random.choice(names))
		index = names.index(raffle_winner_name)
		winner_number = numbers_raffle[index]
		if((str(winner_number)).isdigit()):
			message = client.sms.messages.create(body="Congratulations, you have won.", to='%s' % (winner_number), from_='%s%s' % ('+', raffle_number))
		incoming_data_user.append("%s" % (raffle_winner_name))
		incoming_data_user.append("%s" % (winner_number))
		incoming_data_user.append("onFinish")
		incoming_data_user.append("%s" % (index))
		channel.send_message('Raffle', "%s" % (json.dumps(incoming_data_user)))
		channel.send_message('Raffle_User', "%s" % (json.dumps(incoming_data_user)))
		incoming_raffle_numbers.clear()
		del incoming_data_user[0:len(incoming_data_user)]
		raffle_number = 0			

		
# URL Mapping
app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/profile', Profile), ('/save', Twilio_Save), ('/generate_number', Generate_Number), ('/auto_reply', Auto_Reply_Sms), ('/choose_number', Choose_Number), ('/poll_number', Poll_Number), ('/poll', Twilio_Poll), ('/option_save', Option_Save), ('/Start_Poll', Start_Poll), ('/add_sms_url', Add_Sms_URL), ('/stop_poll', Stop_Poll), ('/results/(\d+)', Permalink), ('/poll_history', Poll_History), ('/auto_reply_raffle', Auto_Reply_Sms_Raffle), ('/Start_Raffle', Start_Raffle), ('/stop_raffle', Stop_Raffle), ('/delete_poll/(\d+)', Delete_Poll), ('/raffle/(\w+)', Start_Raffle_User), ('/update_user_page', Update_User_Raffle_Page), ('/polling/(\w+)', Start_Poll_User)
], debug=True)
 