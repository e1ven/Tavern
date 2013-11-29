from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.parse
import urllib.error
import socket
socket.setdefaulttimeout(30)
from libs import Robohash
import base64
import io
import tavern

class Embedis:

    """Embedis is a quick class/API for translating embeddable media."""

    def __init__(self, x=640, y=480):

        self.server = tavern.Server()

        self.x = str(x)
        self.y = str(y)

        self.functionlist = [self.youtube,
                             self.vimeo,
                             self.embedis,
                             ]

   # @tavern.utils.memorise(ttl=self.server.serversettings.settings['cache']['embedded']['seconds'], maxsize=tavern.singleserv.serversettings.settings['cache']['embedded']['size'])
    def lookup(self, url):
        self.url = url
        self.query = urlparse(url)

        for function in self.functionlist:
            result = function()
            if result is not None:
                return result
        return None

    def youtube(self):
        yid = None
        if self.query.hostname == 'youtu.be':
            yid = self.query.path[1:]
        if self.query.hostname in ('www.youtube.com', 'youtube.com'):
            if self.query.path == '/watch':
                p = parse_qs(self.query.query)
                yid = p['v'][0]
            if self.query.path[:7] == '/embed/':
                yid = self.query.path.split('/')[2]
            if self.query.path[:3] == '/v/':
                yid = self.query.path.split('/')[2]
        # fail?
        if yid is None:
            return None
        else:
            return (
                "<iframe class='youtube-player' type='text/html' width='" + self.x + "' height='" + self.y +
                "' src='https://www.youtube.com/embed/" +
                yid + "?wmode=opaque' frameborder='0'></iframe>"
            )

    def vimeo(self):
        if self.query.hostname in ('vimeo.com', 'www.vimeo.com'):
            possibleid = self.query.path.split('/')[1]
            # If we can convert it to a str and back, it's an int, so likely a
            # video.
            testid = "foo"
            try:
                testid = str(int(possibleid))
            except ValueError:
                return None
            if testid == possibleid:
                return (
                    "<iframe src='https://player.vimeo.com/video/" + possibleid + "' width='" +
                    self.x + "' height='" + self.y +
                    "' frameborder='0' ></iframe>"
                )
            return None
        else:
            return None

    def embedis(self):
        """Embed.is integration."""
        api_url = self.server.serversettings.settings['embedserver'] + \
            '/iframe/' + self.x + '/' + self.y + '/'
        full_url = api_url + self.url
        req = urllib.request.Request(full_url)
        try:
            f = urllib.request.urlopen(req)
            if f.getcode() == 200:
                response = f.read().decode('utf-8')
                f.close()
                self.server.logger.info("Embedis gave us - " + response)
                return response
            else:
                self.server.logger.info(
                    "No good from " + self.server.serversettings.settings['embedserver'])
                f.close()
                return None
        except:
            return None

   # @tavern.utils.memorise(ttl=self.server.serversettings.settings['cache']['avatarcache']['seconds'], maxsize=self.server.serversettings.settings['cache']['avatarcache']['size'])
    def getavatar(self, myid, datauri=True, width=40, height=40):
        """Retrieve the Avatar from Robohash.org, for use in the datauri
        embed."""
        # If user.datauri is True, generate the image and hand it back.
        if datauri:

            format = 'png'
            robo = Robohash.Robohash(myid)
            robo.assemble(
                roboset='any',
                format=format,
                bgset='any',
                sizex=width,
                sizey=height)

            # Encode the Robot to a DataURI
            fakefile = io.BytesIO()
            robo.img.save(fakefile, format=format)
            fakefile.seek(0)
            b64ver = base64.b64encode(fakefile.read())
            b64ver = b64ver.decode('utf-8')
            return("data:image/png;base64," + str(b64ver))

        else:
            avlink = '/avatar/' + myid + \
                '.png?set=any&bgset=any&size=' + str(width) + 'x' + str(height)
            return avlink