import platform
import json
import collections
from collections import OrderedDict
import getpass
import libtavern.utils
import os
import multiprocessing

class ServerSettings(libtavern.utils.instancer):

    def __init__(self,slot='default'):

        super().__init__(slot)
        
        # Don't run __init__ more than once, since we return the same one.
        if self.__dict__.get('set') is True:
            return
        else:
            self.set = True

        self.settingsdir = 'conf/'
        self.settingsfile = slot + ".serversettings"
        self.settings = OrderedDict()
        self.loadconfig(filename=self.settingsfile)
    
    def loadconfig(self, filename=None, directory=None):

        if filename is None:
            filename = self.settingsfile
        if directory is None:
            directory = self.settingsdir

        try:
            filehandle = open(directory + filename, 'r')
            filecontents = filehandle.read()
            self.settings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
            filehandle.close()
        except:
            self.updateconfig()
            self.saveconfig()
            pass
        
        # Always ensure we have all variables, to deal with schema upgrades, etc.
        if self.updateconfig():
           self.saveconfig()

        
    def saveconfig(self, filename=None, directory=None):

        if filename is None:
            filename = self.settingsfile
        if directory is None:
            directory = self.settingsdir

        newsettings = self.settings

        filehandle = open(directory + filename, 'w')
        filehandle.write(
            json.dumps(newsettings, separators=(',', ':')))
        filehandle.close()

    def updateconfig(self):

        # Create a string/immutable version of ServerSettings that we can
        # compare against later to see if anything changed.
        tmpsettings = str(self.settings)

        if not 'hostname' in self.settings:
            self.settings['hostname'] = platform.node()
        if not 'user' in self.settings:
            self.settings['user'] = getpass.getuser()
        if not 'path' in self.settings:
            # Find the root dir where we're running.
            absolutedir = os.path.dirname(os.path.realpath(__file__))
            rootdir = os.path.abspath(os.path.join(absolutedir, os.pardir))
            self.settings['path'] = rootdir
        if not 'ip_listen_on' in self.settings:
            self.settings['ip_listen_on'] = '0.0.0.0'

        # # Which daemons should we start up
        # if not 'processes' in self.settings:
        #     self.settings['processes'] = {}
        # if not 'nginx' in self.settings['processes']:
        #     self.settings['processes']['nginx'] = True
        # if not 'mongo' in self.settings['processes']:
        #     self.settings['processes']['mongo'] = True
   

        if not 'webtav' in self.settings:
            self.settings['webtav'] = {}
        if not 'workers' in self.settings['webtav']:
            self.settings['webtav']['workers'] = multiprocessing.cpu_count()
        if not 'downloads_url' in self.settings['webtav']:
            self.settings['webtav']['downloads_url'] = '/binaries/'
        if not 'main_url' in self.settings['webtav']:
            self.settings['webtav']['main_url'] = None
        if not 'canonical_url' in self.settings['webtav']:
            # The Canonical URL is specified so that Google won't detect duplicate
            # content for every Tavern server, and penalize.
            self.settings['webtav']['canonical_url'] = "https://tavern.is"
        if not 'scheme' in self.settings['webtav']:
            self.settings['webtav']['scheme'] = 'http'
        if not 'session_lifetime' in self.settings['webtav']:
            # Keep Permanent sessions around ~forever, since users might not -have- passwords
            self.settings['webtav']['session_lifetime'] = 31536000 * 20
        if not 'port' in self.settings:
            # Externally Facing Port for nginx
            self.settings['webtav']['port'] = 8000
        if not 'appport' in self.settings:
            # webtav will be started on the port specified, +1 for each worker.
            self.settings['webtav']['appport'] = 8080

        # Default Tornado settings. Put here to let people override.
        if not 'tornado' in self.settings['webtav']:
            self.settings['webtav']['tornado'] = {}
        if not 'cookie_secret' in self.settings['webtav']['tornado']:
             self.settings['webtav']['tornado']['cookie_secret'] = libtavern.utils.randstr(255)
        if not 'xsrf_cookies' in self.settings['webtav']['tornado']:
            self.settings['webtav']['tornado']['xsrf_cookies'] = True
        if not 'gzip' in self.settings['webtav']['tornado']:
            self.settings['webtav']['tornado']['gzip'] = True
        if not 'static_path' in self.settings['webtav']['tornado']:
            self.settings['webtav']['tornado']['static_path'] = 'tmp/static'


        # Set the default DBs
        if not 'DB' in self.settings:
            self.settings['DB'] = {}
        
        if not 'default' in self.settings['DB']:
            self.settings['DB']['default'] = {}
        if not 'type' in self.settings['DB']['default']:
            self.settings['DB']['default']['type'] = 'mongo'
            self.settings['DB']['default']['local'] = True

        if not 'binaries' in self.settings['DB']:
            self.settings['DB']['binaries'] = {}
        if not 'type' in self.settings['DB']['binaries']:
            self.settings['DB']['binaries']['type'] = 'mongo'
            self.settings['DB']['binaries']['local'] = True

        if not 'sessions' in self.settings['DB']:
            self.settings['DB']['sessions'] = {}
        if not 'type' in self.settings['DB']['sessions']:
            self.settings['DB']['sessions']['type'] = 'mongo'
            self.settings['DB']['sessions']['local'] = True

        # Set up the various MongoDBs    
        if not 'mongo' in self.settings:
            self.settings['mongo'] = {}
        
        if not 'default' in self.settings['mongo']:
            self.settings['mongo']['default'] = {}
        if not 'hostname' in self.settings['mongo']['default']:
            self.settings['mongo']['default']['hostname'] = 'localhost'
        if not 'port' in self.settings['mongo']['default']:
            self.settings['mongo']['default']['port'] = 27017
        if not 'name' in self.settings['mongo']['default']:
            self.settings['mongo']['default']['name'] = 'Tavern'
        if not 'connections' in self.settings['mongo']['default']:
            self.settings['mongo']['default']['connections'] = 10

        if not 'binaries' in self.settings['mongo']:
            self.settings['mongo']['binaries'] = {}
        if not 'hostname' in self.settings['mongo']['binaries']:
            self.settings['mongo']['binaries']['hostname'] = 'localhost'
        if not 'port' in self.settings['mongo']['binaries']:
            self.settings['mongo']['binaries']['port'] = 27017
        if not 'name' in self.settings['mongo']['binaries']:
            self.settings['mongo']['binaries']['name'] = 'Tavern-Binaries'
        if not 'connections' in self.settings['mongo']['binaries']:
            self.settings['mongo']['binaries']['connections'] = 10

        if not 'sessions'in self.settings['mongo']:
            self.settings['mongo']['sessions'] = {}
        if not 'hostname' in self.settings['mongo']['sessions']:
            self.settings['mongo']['sessions']['hostname'] = 'localhost'
        if not 'port' in self.settings['mongo']['sessions']:
            self.settings['mongo']['sessions']['port'] = 27017
        if not 'name' in self.settings['mongo']['sessions']:
            self.settings['mongo']['sessions']['name'] = 'Tavern-Sessions'
        if not 'connections' in self.settings['mongo']['sessions']:
            self.settings['mongo']['sessions']['connections'] = 10


        # Set up the various PostgresDBs    
        if not 'postgres' in self.settings:
            self.settings['postgres'] = {}

        if not 'default' in self.settings['postgres']:
            self.settings['postgres']['default'] = {}
        if not 'hostname' in self.settings['postgres']['default']:
            self.settings['postgres']['default']['hostname'] = 'localhost'
        if not 'user' in self.settings['postgres']['default']:
            self.settings['postgres']['default']['user'] = self.settings['user']
        if not 'hostname' in self.settings['postgres']['default']:
            self.settings['hostname'] = "localhost"
        if not 'name' in self.settings['postgres']['default']:
            self.settings['postgres']['default']['name'] = 'Tavern'
        if not 'port' in self.settings['postgres']['default']:
            self.settings['postgres']['default']['port'] = 5432
        if not 'connections' in self.settings['postgres']['default']:
            self.settings['postgres']['default']['connections'] = 10


        # Set up the various Nginx settings    
        if not 'nginx' in self.settings:
            self.settings['nginx'] = {}
        if not 'workers' in self.settings['nginx']:
            self.settings['nginx']['workers'] = multiprocessing.cpu_count()
        if not 'worker_connections' in self.settings['nginx']:
            import resource
            max_files_soft = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            max_files_hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]

            # wc is the total number of connections each worker can hold open, 
            # including connections downstream to tornado.
            wc = self.settings['webtav']['workers'] * 10000
            self.settings['nginx']['worker_connections'] = wc
        if not 'worker_rlimit_nofile' in self.settings['nginx']:
            self.settings['nginx']['worker_rlimit_nofile'] = self.settings['nginx']['worker_connections'] * self.settings['nginx']['workers']
        if not 'sitefile' in self.settings['nginx']:
            self.settings['nginx']['sitefile'] = 'default.site'


        # Logging

        if not 'logfile' in self.settings:
            self.settings['logfile'] = "logs/" + self.settings['hostname'] + '.log'

        if not 'loglevel' in self.settings:
            self.settings['loglevel'] = "INFO"



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

        # Settings related to the Web View
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

        if not 'get_all_user_posts' in self.settings['cache']:
            self.settings['cache']['get_all_user_posts'] = {}
            self.settings['cache']['get_all_user_posts']['size'] = 10000
            self.settings['cache']['get_all_user_posts']['seconds'] = 2

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

        if not 'KeyGenerator' in self.settings:
            self.settings['KeyGenerator'] = {}
        if not 'num_pregens' in self.settings['KeyGenerator']:
            self.settings['KeyGenerator']['num_pregens'] = 5
        if not 'workers' in self.settings['KeyGenerator']:
            self.settings['KeyGenerator']['workers'] = 1

        if not 'keys' in self.settings:
            self.settings['keys'] = {}
        if not 'keysize' in self.settings['keys']:
            self.settings['keys']['keysize'] = 3072

        if not 'upload-dir' in self.settings:
            self.settings['upload-dir'] = '../nginx/uploads'

        if not 'mark-origin' in self.settings:
            self.settings['mark-origin'] = False

        if not 'mark-seen' in self.settings:
            self.settings['mark-seen'] = False

        if not 'max-upload-preview-size' in self.settings:
            self.settings['max-upload-preview-size'] = 10485760

        if not 'embedserver' in self.settings:
            self.settings['embedserver'] = 'http://embed.is'

        if not 'maxembeddedurls' in self.settings:
            self.settings['maxembeddedurls'] = 10

        if not 'proof-of-work-difficulty' in self.settings:
            self.settings['proof-of-work-difficulty'] = 19


        # These users are created by the server on startup.

        if not 'guestuser' in self.settings:
            self.settings['guestuser'] = {}
        if not 'pubkey' in self.settings['guestuser']:
            self.settings['guestuser']['pubkey'] = None
        if not 'passkey' in self.settings['guestuser']:
            self.settings['guestuser']['passkey'] = None

        if not 'defaultuser' in self.settings:
            self.settings['defaultuser'] = {}
        if not 'pubkey' in self.settings['defaultuser']:
            self.settings['defaultuser']['pubkey'] = None
        if not 'passkey' in self.settings['defaultuser']:
            self.settings['defaultuser']['passkey'] = None


        # Report back on if there were any changes.
        if str(self.settings) == tmpsettings:
            return False
        else:
            return True