from collections import OrderedDict
import platform
import json
import collections
from collections import OrderedDict
import TavernUtils
import socket
import getpass

class ServerSettings():

    def __init__(self):
        self.settings = OrderedDict()
        self.loadconfig()
        
    def loadconfig(self, filename=None,directory='data/conf/'):

        if filename is None:
            filename = platform.node() + ".TavernServerSettings"

        try:
            filehandle = open(directory + filename, 'r')
            filecontents = filehandle.read()
            self.settings = json.loads(filecontents, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
            filehandle.close()
        except:
            print("Error opening config file. Making New one.")
            pass

        self.updateconfig()
        self.saveconfig()

    def saveconfig(self, filename=None,directory='data/conf/'):
        newsettings = self.settings
        newsettings['temp'] = {}

        if filename is None:
            filename = self.settings['hostname'] + \
                ".TavernServerSettings"

        filehandle = open(directory + filename, 'w')
        filehandle.write(
            json.dumps(newsettings, separators=(',', ':')))
        filehandle.close()

    def updateconfig(self):
        
        if not 'temp' in self.settings:
            self.settings['temp'] = {}

        if not 'hostname' in self.settings:
            self.settings['hostname'] = platform.node()

        if not 'primaryurl' in self.settings:
            self.settings['primaryurl'] = False

        if not 'downloadsurl' in self.settings:
            self.settings['downloadsurl'] = '/binaries/'
     
                    
        if not 'logfile' in self.settings:
            self.settings[
                'logfile'] = "logs/" + self.settings['hostname'] + '.log'

        if not 'loglevel' in self.settings:
            self.settings[
                'loglevel'] = "INFO"


        if not 'mongo-hostname' in self.settings:
            self.settings['mongo-hostname'] = 'localhost'
        if not 'mongo-port' in self.settings:
            self.settings['mongo-port'] = 27017


        if not 'postgres-hostname' in self.settings:
            self.settings['postgres-hostname'] = 'localhost'
        if not 'postgres-user' in self.settings:
            self.settings['postgres-user'] = getpass.getuser()
        if not 'postgres-hostname' in self.settings:
            self.settings['postgres-hostname'] = "localhost"
        if not 'postgres-port' in self.settings:
            self.settings['postgres-port'] = 5432
            
   

        if not 'dbname' in self.settings:
            self.settings['dbname'] = 'Tavern'


        if not 'bin-mongo-hostname' in self.settings:
            self.settings['bin-mongo-hostname'] = 'localhost'
        if not 'bin-mongo-port' in self.settings:
            self.settings['bin-mongo-port'] = 27017
        if not 'bin-mongo-db' in self.settings:
            self.settings['bin-mongo-db'] = 'Tavern-Binaries'
        if not 'sessions-mongo-hostname' in self.settings:
            self.settings['sessions-mongo-hostname'] = 'localhost'
        if not 'sessions-mongo-port' in self.settings:
            self.settings['sessions-mongo-port'] = 27017
        if not 'sessions-mongo-db' in self.settings:
            self.settings['sessions-mongo-db'] = 'Tavern-Sessions'

        if not 'cache' in self.settings:
            self.settings['cache'] = {}

        if not 'user-trust' in self.settings['cache']:
            self.settings['cache']['user-trust'] = {}
            self.settings['cache']['user-trust']['seconds'] = 300
            self.settings['cache']['user-trust']['size'] = 10000

        if not 'message-ratings' in self.settings['cache']:
            self.settings['cache']['message-ratings'] = {}
            self.settings['cache']['message-ratings']['seconds'] = 300
            self.settings['cache']['message-ratings']['size'] = 10000

        if not 'avatarcache' in self.settings['cache']:
            self.settings['cache']['avatarcache'] = {}
            self.settings['cache']['avatarcache']['size'] = 100000
            self.settings['cache']['avatarcache']['seconds'] = None

        if not 'embedded' in self.settings['cache']:
            self.settings['cache']['embedded'] = {}
            self.settings['cache']['embedded']['size'] = 1000
            self.settings['cache']['embedded']['seconds'] = 3601

        if not 'user-note' in self.settings['cache']:
            self.settings['cache']['user-note'] = {}
            self.settings['cache']['user-note']['size'] = 10000
            self.settings['cache']['user-note']['seconds'] = 60

        if not 'subjects-in-topic' in self.settings['cache']:
            self.settings['cache']['subjects-in-topic'] = {}
            self.settings['cache']['subjects-in-topic']['size'] = 1000
            self.settings['cache']['subjects-in-topic']['seconds'] = 1

        if not 'toptopics' in self.settings['cache']:
            self.settings['cache']['toptopics'] = {}
            self.settings['cache']['toptopics']['size'] = 1
            self.settings['cache']['toptopics']['seconds'] = 3602


        ##### Settings related to the Web View
        if not 'templates' in self.settings['cache']:
            self.settings['cache']['templates'] = {}
            self.settings['cache']['templates']['size'] = 1000
            self.settings['cache']['templates']['seconds'] = 5


        if not 'getpagelemenent' in self.settings['cache']:
            self.settings['cache']['getpagelemenent'] = {}
            self.settings['cache']['getpagelemenent']['size'] = 1000
            self.settings['cache']['getpagelemenent']['seconds'] = 20

        if not 'message-page' in self.settings['cache']:
            self.settings['cache']['message-page'] = {}
            self.settings['cache']['message-page']['size'] = 1000
            self.settings['cache']['message-page']['seconds'] = 1
        
        if not 'topic-page' in self.settings['cache']:
            self.settings['cache']['topic-page'] = {}
            self.settings['cache']['topic-page']['size'] = 1000
            self.settings['cache']['topic-page']['seconds'] = 1







        if not 'uasparser' in self.settings['cache']:
            self.settings['cache']['uasparser'] = {}
            self.settings['cache']['uasparser']['size'] = 1000
            self.settings['cache']['uasparser']['seconds'] = 36001

        if not 'topiccount' in self.settings['cache']:
            self.settings['cache']['topiccount'] = {}
            self.settings['cache']['topiccount']['size'] = 1000
            self.settings['cache']['topiccount']['seconds'] = 10

        if not 'receiveEnvelope' in self.settings['cache']:
            self.settings['cache']['receiveEnvelope'] = {}
            self.settings['cache']['receiveEnvelope']['size'] = 10000
            self.settings['cache']['receiveEnvelope']['seconds'] = 1000

        if not 'getUsersPosts' in self.settings['cache']:
            self.settings['cache']['getUsersPosts'] = {}
            self.settings['cache']['getUsersPosts']['size'] = 10000
            self.settings['cache']['getUsersPosts']['seconds'] = 2

        if not 'sorttopic' in self.settings['cache']:
            self.settings['cache']['sorttopic'] = {}
            self.settings['cache']['sorttopic']['size'] = 1000000
            self.settings['cache']['sorttopic']['seconds'] = 10000000000

        if not 'formatText' in self.settings['cache']:
            self.settings['cache']['formatText'] = {}
            self.settings['cache']['formatText']['size'] = 1000
            self.settings['cache']['formatText']['seconds'] = 10000000000

        if not 'error_envelope' in self.settings['cache']:
            self.settings['cache']['error_envelope'] = {}
            self.settings['cache']['error_envelope']['size'] = 20
            self.settings['cache']['error_envelope']['seconds'] = 10000000000




        if not 'UserGenerator' in self.settings:
            self.settings['UserGenerator'] = {}
        if not 'num_pregens' in self.settings['UserGenerator']:
            self.settings['UserGenerator']['num_pregens'] = 5
        if not 'workers' in self.settings['UserGenerator']:
            self.settings['UserGenerator']['workers'] = 1
        if not 'sleep' in self.settings['UserGenerator']:
            self.settings['UserGenerator']['sleep'] = 5


        if not 'upload-dir' in self.settings:
            self.settings['upload-dir'] = '/opt/uploads'

        if not 'mark-origin' in self.settings:
            self.settings['mark-origin'] = False

        if not 'mark-seen' in self.settings:
            self.settings['mark-seen'] = False

        if not 'max-upload-preview-size' in self.settings:
            self.settings['max-upload-preview-size'] = 10485760

        if not 'cookie-encryption' in self.settings:
            self.settings['cookie-encryption'] = TavernUtils.randstr(255)
        if not 'serverkey-password' in self.settings:
            self.settings[
                'serverkey-password'] = TavernUtils.randstr(255)
        if not 'embedserver' in self.settings:
            self.settings['embedserver'] = 'http://embed.is'

        if not 'maxembeddedurls' in self.settings:
            self.settings['maxembeddedurls'] = 10

        if not 'mongo-connections' in self.settings:
            self.settings['mongo-connections'] = 10

        if not 'dbtype' in self.settings:
            self.settings['dbtype'] = 'mongo'

        if not 'proof-of-work-difficulty' in self.settings:
            self.settings['proof-of-work-difficulty'] = 19



serversettings = ServerSettings()
