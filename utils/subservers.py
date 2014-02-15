import libtavern
import libtavern.serversettings
import optparse
import socket
import os
import subprocess
import signal
import errno
import time
import sys

def process_running(pid):
    """Check whether pid exists."""
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            raise
    else:
        return True


class process(object):
    def get_pid_status(self):
        self.pid = None
        if os.path.isfile(self.pidpath):
            with open(self.pidpath,'r') as f:
                self.pid = int(f.read())
            if not process_running(self.pid):
                os.remove(self.pidpath)
                self.pid = None

    def stop(self):
        """
        Stop the version of mongo bundled with Tavern
        """
        self.get_pid_status()
        state = self.pid
        if self.pid is not None:
            os.kill(int(self.pid), signal.SIGTERM)
            print("Asked " + str(self.__class__.__name__) + " to stop.")
        self.get_pid_status()
           

    def status(self):
        """
        Is the app running?
        """
        self.get_pid_status()
        if self.pid is not None:
            print(str(self.__class__.__name__) + " started with pid " + str(self.pid))
        else:
            print(str(self.__class__.__name__) + " is not running.")

    def makedirs(self,path,exist_ok):
        """
        Calls os.makedirs.

        Added because os.makedirs will complain if the directory already exists, but has different perms.
        Even if I don't specify any perms ;( It will default to umask, then complain.
        See http://bugs.python.org/issue13498
        """
        try:
            os.makedirs(path,exist_ok)
        except FileExistsError:
            pass

class Nginx(process):

    def __init__(self):
        # Load in the settings
        self.serversettings = libtavern.serversettings.ServerSettings()
        self.serversettings.loadconfig()

        self.binpath = self.serversettings.settings['path'] + '/utils/nginx/sbin/nginx'
        self.configpath = self.serversettings.settings['path'] + '/tmp/nginx.conf'
        self.config2path = self.serversettings.settings['path'] + '/tmp/listen.conf'
        self.pidpath = self.serversettings.settings['path'] + '/tmp/nginx.pid'
        self.get_pid_status()

    def write_config(self):
        """
        Create a nginx.conf file for this Tavern server.
        """

        # Write out the config file which says which port/ip to listen on.
        # This has to be a separate file, since it is dynamic, 
        # whereas the .site file is static
        with open(self.config2path,'w') as f:
            print("listen " + self.serversettings.settings['ip_listen_on'] + ":" + str(self.serversettings.settings['webtav']['port']) + ";",file=f)

        # Write out the main nginx.conf file
        with open(self.configpath, 'w') as f:
            print("""
            worker_processes """ + str(self.serversettings.settings['nginx']['workers']) + """;
            events {
                worker_connections """ + str(self.serversettings.settings['nginx']['worker_connections']) + """;
            }
            worker_rlimit_nofile """ + str(self.serversettings.settings['nginx']['worker_rlimit_nofile']) + """;
            error_log  """ + self.serversettings.settings['path'] + """/logs/nginx-error.log;
            pid        """ + self.pidpath + """;

            http {
                access_log  """ + self.serversettings.settings['path'] + """/logs/nginx-access.log;
                upstream  tornados {
            """,file=f)


            # Define the upstream listeners.
            # This is where nginx hands off to Tornado, using Unix domain sockets
            for instance in range(0,self.serversettings.settings['webtav']['workers']):
                socketfile = self.serversettings.settings['path'] + "/tmp/webtav-worker-" + str(instance) + ".sock"
                print("\t\t\t\tserver unix:" + socketfile + ";",file=f)

            print("""
                    }
                server_name_in_redirect off;
                server_tokens off;

                # 10 minutes, 100Mb.
                proxy_cache_path """ + self.serversettings.settings['path'] + """/tmp/default-cache levels=1:2 keys_zone=default-cache:10m max_size=100m;
                proxy_cache_path """ + self.serversettings.settings['path'] + """/tmp/avatar-cache levels=1:2 keys_zone=avatar-cache:9000m max_size=700m;
                proxy_cache_path """ + self.serversettings.settings['path'] + """/tmp/binaries-cache levels=1:2 keys_zone=binaries-cache:90m max_size=2000m;
                proxy_temp_path """ + self.serversettings.settings['path'] + """/tmp/nginxcache;

                proxy_buffer_size   128k;
                proxy_buffers   4 256k;
                proxy_busy_buffers_size   256k;

                open_file_cache           max=1000 inactive=20s;
                open_file_cache_valid     30s;
                open_file_cache_min_uses  2;
                open_file_cache_errors    on;
                default_type  application/octet-stream;

                sendfile        on;
                tcp_nopush     on;

                keepalive_timeout  65;
                gzip  off;
                include """ +  self.serversettings.settings['path'] + """/conf/nginx/mime.types;
                include """ + self.serversettings.settings['path'] + "/conf/nginx/" + self.serversettings.settings['nginx']['sitefile'] + """;
                }""",file=f)

        # Ensure we have the dirs necessary to run mongo.
        self.makedirs(self.serversettings.settings['path'] + '/logs/',exist_ok=True)
        self.makedirs(self.serversettings.settings['path'] + '/conf/',exist_ok=True)
        self.makedirs(self.serversettings.settings['path'] + '/tmp/nginxcache',exist_ok=True)

    def start(self):
        """
        Start the version of mongo bundled with Tavern
        """

        self.get_pid_status()
        if self.pid is not None:
            print("Nginx is already running on pid " + str(self.pid))
            return

        print(self.configpath)
        subprocess.Popen([self.binpath,"-c",self.configpath])


        # Wait for nginx to start, so we can get the pid
        loops = 0
        while self.pid is None:
            self.get_pid_status()

            loops += 1
            time.sleep(.2)
            if loops > 100:
                print("Error starting Nginx")
                return False
                
        self.get_pid_status()
        print("Nginx started with pid " + str(self.pid))
 

class MongoDB(process):

    def __init__(self):

        # Load in the settings
        self.serversettings = libtavern.serversettings.ServerSettings()
        self.serversettings.loadconfig()

        self.binpath = self.serversettings.settings['path'] + '/utils/mongodb/bin/mongod'
        self.configpath = self.serversettings.settings['path'] + '/tmp/mongodb.conf' 
        self.pidpath = self.serversettings.settings['path'] + '/tmp/mongod.pid'
        self.get_pid_status()


    def write_config(self):
        """
        Create a mongodb.conf file for this Tavern server.
        """

        finalport = None
        ips = set()

        # Get a list of DBs that we should start locally.
        for key in self.serversettings.settings['DB']:
            if self.serversettings.settings['DB'][key]['local'] and self.serversettings.settings['DB'][key]['type'] == 'mongo':
                hostname = self.serversettings.settings['mongo'][key]['hostname']
                ip = socket.gethostbyname(hostname)
                ips.add(ip)

                port = self.serversettings.settings['mongo'][key]['port']
                if finalport is None:
                    finalport = port
                else:
                    if finalport != port:
                        raise('FileGeneratorException','More than')

        ipscsv = ",".join(ips)

        with open(self.configpath, 'w') as f:
            print('port='+str(finalport),file=f)
            print('bind_ip='+ipscsv,file=f)
            print('logpath='+self.serversettings.settings['path'] + '/logs/mongod.log',file=f)
            print('pidfilepath='+self.pidpath,file=f)
            print('dbpath='+self.serversettings.settings['path'] + '/datafiles/mongodb',file=f)
            print('nounixsocket=true',file=f)
            print('fork=true',file=f)


        # Ensure we have the dirs necessary to run mongo.
        self.makedirs(self.serversettings.settings['path'] + '/logs/',exist_ok=True)
        self.makedirs(self.serversettings.settings['path'] + '/conf/',exist_ok=True)
        self.makedirs(self.serversettings.settings['path'] + '/datafiles/mongodb',exist_ok=True)


    def start(self):
        """
        Start the version of mongo bundled with Tavern
        """
        self.get_pid_status()
        if self.pid is not None:
            print("Mongo is already running on pid " + str(self.pid))
            return

        subprocess.Popen([self.binpath,"--config",self.configpath])
        print("Mongo started with pid " + str(self.pid))



def main():
    parser = optparse.OptionParser(add_help_option=False, description="Create MongoDB conf file for Tavern")
    parser.add_option("-p", "--port", action="store", dest="port", default=None,
                      help="Force MongoDB to use port.")
    parser.add_option("-l", "--listen", action="store", dest="listen", default=None,
                      help="Force MongoDB to listen on IP.")

    parser.add_option("-?", "--help", action="help",
                      help="Show this helpful message.")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        print ("Must have at least one command, such as start/stop/status")
        sys.exit(2)

    mongo = MongoDB()
    mongo.write_config()

    nginx = Nginx()
    nginx.write_config()

    if args[0].lower() == 'start':
        nginx.start()
        mongo.start()
    elif args[0].lower() == 'stop':
        nginx.stop()
        mongo.stop()
    elif args[0].lower() == 'status':
        nginx.status()
        mongo.status()



    

if __name__ == "__main__":
    main()