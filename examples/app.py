from flask import Flask
from flask.ext.simplerest import RestAPI, RestView

app = Flask(__name__)
rest = RestAPI(app)

import datetime
from random import randint
class ComplexObject(object):
	dt_start = None

	def __init__(self, id):
		self.id = id
		self.dt_start = datetime.datetime.now()

	def to_json(self):
		return self.__dict__

# ------------- Views ------------- #

class SampleView(RestView):
	def index(self):
		return [ ComplexObject(i) for i in range(1,3)]

	def message(self, msg):
		if not msg:
			msg = 'Hello World'
		return dict(message="I say: %s" % msg)

rest.register(SampleView)

if __name__ == '__main__':
	app.run(debug=True)