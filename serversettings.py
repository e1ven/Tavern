from collections import OrderedDict
import platform
import json
import collections
from collections import OrderedDict
import TavernUtils


class ServerSettings():

    def __init__(self):
        self.ServerSettings = OrderedDict()

    def loadconfig(self, filename=None):
        if filename is None:
            filename = platform.node() + ".TavernServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        filehandle.close()
        self.updateconfig()
        self.saveconfig()

    def saveconfig(self, filename=None):
        if filename is None:
            filename = self.ServerSettings['hostname'] + \
                ".TavernServerSettings"
        filehandle = open(filename, 'w')
        filehandle.write(
            json.dumps(self.ServerSettings, separators=(',', ':')))
        filehandle.close()

    def updateconfig(self):

     #   self.logger.info("Generating any missing config values")

        if not 'hostname' in self.ServerSettings:
            self.ServerSettings['hostname'] = platform.node()
        if not 'logfile' in self.ServerSettings:
            self.ServerSettings[
                'logfile'] = self.ServerSettings['hostname'] + '.log'
        if not 'mongo-hostname' in self.ServerSettings:
            self.ServerSettings['mongo-hostname'] = 'localhost'
        if not 'mongo-port' in self.ServerSettings:
            self.ServerSettings['mongo-port'] = 27017
        if not 'dbname' in self.ServerSettings:
            self.ServerSettings['dbname'] = 'Tavern'
        if not 'bin-mongo-hostname' in self.ServerSettings:
            self.ServerSettings['bin-mongo-hostname'] = 'localhost'
        if not 'bin-mongo-port' in self.ServerSettings:
            self.ServerSettings['bin-mongo-port'] = 27017
        if not 'bin-mongo-db' in self.ServerSettings:
            self.ServerSettings['bin-mongo-db'] = 'Tavern-Binaries'
        if not 'sessions-mongo-hostname' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-hostname'] = 'localhost'
        if not 'sessions-mongo-port' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-port'] = 27017
        if not 'sessions-mongo-db' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-db'] = 'Tavern-Sessions'

        if not 'cache' in self.ServerSettings:
            self.ServerSettings['cache'] = {}

        if not 'user-trust' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-trust'] = {}
            self.ServerSettings['cache']['user-trust']['seconds'] = 300
            self.ServerSettings['cache']['user-trust']['size'] = 10000

        if not 'user-ratings' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-ratings'] = {}
            self.ServerSettings['cache']['user-ratings']['seconds'] = 300
            self.ServerSettings['cache']['user-ratings']['size'] = 10000

        if not 'avatarcache' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['avatarcache'] = {}
            self.ServerSettings['cache']['avatarcache']['size'] = 100000
            self.ServerSettings['cache']['avatarcache']['seconds'] = None

        if not 'embedded' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['embedded'] = {}
            self.ServerSettings['cache']['embedded']['size'] = 1000
            self.ServerSettings['cache']['embedded']['seconds'] = 3600

        if not 'user-note' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-note'] = {}
            self.ServerSettings['cache']['user-note']['size'] = 10000
            self.ServerSettings['cache']['user-note']['seconds'] = 60

        if not 'subjects-in-topic' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['subjects-in-topic'] = {}
            self.ServerSettings['cache']['subjects-in-topic']['size'] = 1000
            self.ServerSettings['cache']['subjects-in-topic']['seconds'] = 30

        if not 'toptopics' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['toptopics'] = {}
            self.ServerSettings['cache']['toptopics']['size'] = 1
            self.ServerSettings['cache']['toptopics']['seconds'] = 3600

        if not 'frontpage' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['frontpage'] = {}
            self.ServerSettings['cache']['frontpage']['size'] = 1000
            self.ServerSettings['cache']['frontpage']['seconds'] = 3600

        if not 'uasparser' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['uasparser'] = {}
            self.ServerSettings['cache']['uasparser']['size'] = 1000
            self.ServerSettings['cache']['uasparser']['seconds'] = 36000

        if not 'upload-dir' in self.ServerSettings:
            self.ServerSettings['upload-dir'] = '/opt/uploads'

        if not 'mark-origin' in self.ServerSettings:
            self.ServerSettings['mark-origin'] = False

        if not 'max-upload-preview-size' in self.ServerSettings:
            self.ServerSettings['max-upload-preview-size'] = 10485760

        if not 'cookie-encryption' in self.ServerSettings:
            self.ServerSettings['cookie-encryption'] = TavernUtils.randstr(255)
        if not 'serverkey-password' in self.ServerSettings:
            self.ServerSettings[
                'serverkey-password'] = TavernUtils.randstr(255)
        if not 'embedserver' in self.ServerSettings:
            self.ServerSettings['embedserver'] = 'http://embed.is'
        if not 'downloadsurl' in self.ServerSettings:
            self.ServerSettings['downloadsurl'] = '/binaries/'
        if not 'maxembeddedurls' in self.ServerSettings:
            self.ServerSettings['maxembeddedurls'] = 10

        if not 'mongo-connections' in self.ServerSettings:
            self.ServerSettings['mongo-connections'] = 10

serversettings = ServerSettings()
