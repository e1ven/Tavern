import json

g = open('example.json', 'r')
filecontents = g.read()
decoded = json.loads(filecontents)
print decoded['pluric_container']['server'][0]
