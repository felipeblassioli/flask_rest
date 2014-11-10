# flask_rest

Develop a restful api with Flask.

Create views that extend RestView and return objects that can be jsonified.

RestView extends [flask-classy.FlaskView](https://github.com/apiguy/flask-classy/)

## Example

```python

# Init where app is instance of Flak

rest = RestAPI(app)

...

class ComplexObject(object):
	dt_start = None

	def __init__(self, id):
		self.id = id
		self.dt_start = datetime.datetime.now()

	# Called by flask.jsonify
	def to_json(self):
		return self.__dict__

class SampleView(RestView):
	def index(self):
		return [ ComplexObject(i) for i in range(1,3)]

	def message(self, msg):
		if not msg:
			msg = 'Hello World'
		return dict(message="I say: %s" % msg)

rest.register(SampleView)
```

### Consuming

```bash
$ curl http://127.0.0.1:5000/sample/

{
  "data": [
    {
      "dt_start": 1415631221094, 
      "id": 1
    }, 
    {
      "dt_start": 1415631221094, 
      "id": 2
    }
  ]
}
```


```bash
$ curl http://127.0.0.1:5000/sample/message/hello

{
  "message": "I say: hello"
}
```

