from clarifai import rest
from clarifai.rest import ClarifaiApp

import clarifai
from clarifai.rest import ClarifaiApp

app = ClarifaiApp(api_key='cd9af066bd5b48bb867c581bb57b7ca7')


model = app.models.get('general-v1.3')

a=model.predict_by_url(url='https://samples.clarifai.com/metro-north.jpg')
print a['outputs'][0]['id']