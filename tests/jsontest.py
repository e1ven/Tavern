import json

#Open our Example JSON file
g = open('example.json', 'r')
filecontents = g.read()

#Create a series of python dictionaries.
decoded = json.loads(filecontents)

#Pull out the Message, and re-JSONify it. 
message = decoded['pluric_container']['message']
#We want it as tight as possible, so it always matches other generated versions.
newstr = json.dumps(message,ensure_ascii=False,separators=(',',':'))
print newstr
