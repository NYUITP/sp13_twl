from google.appengine.ext import db

class Twilio_Info(db.Model):
	#Models an individual Guestbook entry with an author, content, and date.
	#name = db.StringProperty()
	twilio_username = db.StringProperty()
	twilio_password = db.StringProperty()
