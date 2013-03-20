from collections import OrderedDict
import platform
import json
import collections
from collections import OrderedDict
import TavernUtils


class ServerSettings():

    def __init__(self):
        self.settings = OrderedDict()

    def loadconfig(self, filename=None):
        if filename is None:
            filename = platform.node() + ".TavernServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.settings = json.loads(filecontents, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        filehandle.close()
        self.updateconfig()
        self.saveconfig()

    def saveconfig(self, filename=None):
        if filename is None:
            filename = self.settings['hostname'] + \
                ".TavernServerSettings"
        filehandle = open(filename, 'w')
        filehandle.write(
            json.dumps(self.settings, separators=(',', ':')))
        filehandle.close()

    def updateconfig(self):

     #   self.logger.info("Generating any missing config values")

        if not 'hostname' in self.settings:
            self.settings['hostname'] = platform.node()
        if not 'logfile' in self.settings:
            self.settings[
                'logfile'] = self.settings['hostname'] + '.log'
        if not 'mongo-hostname' in self.settings:
            self.settings['mongo-hostname'] = 'localhost'
        if not 'mongo-port' in self.settings:
            self.settings['mongo-port'] = 27017
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

        if not 'user-ratings' in self.settings['cache']:
            self.settings['cache']['user-ratings'] = {}
            self.settings['cache']['user-ratings']['seconds'] = 300
            self.settings['cache']['user-ratings']['size'] = 10000

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

        if not 'templates' in self.settings['cache']:
            self.settings['cache']['templates'] = {}
            self.settings['cache']['templates']['size'] = 1000
            self.settings['cache']['templates']['seconds'] = 1

        if not 'uasparser' in self.settings['cache']:
            self.settings['cache']['uasparser'] = {}
            self.settings['cache']['uasparser']['size'] = 1000
            self.settings['cache']['uasparser']['seconds'] = 36001

        if not 'topiccount' in self.settings['cache']:
            self.settings['cache']['topiccount'] = {}
            self.settings['cache']['topiccount']['size'] = 1000
            self.settings['cache']['topiccount']['seconds'] = 10


        if not 'upload-dir' in self.settings:
            self.settings['upload-dir'] = '/opt/uploads'

        if not 'mark-origin' in self.settings:
            self.settings['mark-origin'] = False

        if not 'max-upload-preview-size' in self.settings:
            self.settings['max-upload-preview-size'] = 10485760

        if not 'cookie-encryption' in self.settings:
            self.settings['cookie-encryption'] = TavernUtils.randstr(255)
        if not 'serverkey-password' in self.settings:
            self.settings[
                'serverkey-password'] = TavernUtils.randstr(255)
        if not 'embedserver' in self.settings:
            self.settings['embedserver'] = 'http://embed.is'
        if not 'downloadsurl' in self.settings:
            self.settings['downloadsurl'] = '/binaries/'
        if not 'maxembeddedurls' in self.settings:
            self.settings['maxembeddedurls'] = 10

        if not 'mongo-connections' in self.settings:
            self.settings['mongo-connections'] = 10

        if not 'dbtype' in self.settings:
            self.settings['dbtype'] = 'mongo'


serversettings = ServerSettings()
