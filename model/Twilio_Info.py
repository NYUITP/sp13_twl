<<<<<<< HEAD
from google.appengine.ext import db

class Twilio_Info(db.Model):
	#Models an individual Guestbook entry with an author, content, and date.
	#name = db.StringProperty()
	twilio_username = db.StringProperty()
	twilio_password = db.StringProperty()
=======
from google.appengine.ext import db

class Twilio_Info(db.Model):
	#Models an individual Twilio credentials entry.
	#name = db.StringProperty()
	twilio_username = db.StringProperty()
	twilio_password = db.StringProperty()
	
class Poll_Data(db.Model):
	#Models an individual Twilio credentials entry.
	#name = db.StringProperty()
	poll_question = db.StringProperty()
	poll_data = db.StringProperty()
	#poll_number = db.PhoneNumberProperty() 
>>>>>>> origin/Suyash
