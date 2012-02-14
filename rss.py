#  Python RSS 2.0 feed generator 
#  Copyright 2009 Zaur Nasibov, http://www.znasibov.info/

# Programmed via  :       Emacs, Ubuntu
# Programming language:   Python 3
# RSS 2.0 specification:  http://cyber.law.harvard.edu/rss/rss.html

# Basic usage example:
#
# channel = rss.Channel('My news feed', 
#                       'http://www.example.com/rss.xml', 
#                       'This is my news feed about...', 
#                       generator = 'rss.py',
#                       pubdate = datetime.datetime.now(),
#                       language = 'en-US')
#
# item = rss.Item(channel, 
#                 'What a sunny day', 
#                 'http://www.example.com/what-a-sunny-day.html',
#                 'It\'s a sunny day, I\'m going for a walk.'
#                 pubdate = datetime.datetime.now())
#
# channel.additem(item)
#
# print(channel.toxml())



from abc import ABCMeta, abstractproperty, abstractmethod
from datetime import datetime
import xml.dom.minidom
import re                      # used in cdata mechanism



class RSSBaseElement(metaclass=ABCMeta):
   """Abstract class for Channel/Item classes

   Both Channel and Item RSS Elements required to have a title, a link and a description.
   Other elements are optional. 
   The RSSBaseElement class provides methods to parse required and optional parameters
   and abstract properties that must be implemented via Channel and Item classes
   """

   def __init__(self, title, link, description, cdata = True, **optional):
      # Required elements
      self.title = title if type(title) == Title else Title(title)
      self.link = link if type(link) == Link else Link(link)
      self.description = description if type(description) == Description else Description(description)

      self._opt = optional     # optional elements, used in self._set
      self._cdata = cdata      # CDATA text nodes flag, is true by-default
      self._pcdata = re.compile(r'("|\'|<|>|&)')        # cdata search regex
      self._built = []         # elements that have been already built

   @abstractproperty
   def document(self):
      """DOM document"""
      pass

   @abstractproperty
   def root(self):
      """DOM documet's RSSBase (Channel or Item) element"""
      pass


   def _set(self, elementclass):             
      """Create an attribute from optional constructor argument(s).
      The attribute refers to an object of RSSElemet subclass type

      elementclass - the module's class that represents an element
      """
      name = elementclass.__name__.lower() # get class's name       

      element = None
      if name in self._opt.keys():        # if element is in optional arguments
         element = self._opt[name]        # get element from optional arguments 
      
      if type(element) == str or \
             type(element) == datetime:   # element has been passed as a string or as a datetime object
         element = elementclass(element)  # initialize a Class

      if type(element) == elementclass:   # element has been passed as an object 
         self.__setattr__(name, element)  # ..or has been created above
      

   def _build(self, elementclass = None):
      """Build DOM structure

      elementclass - specific element's class. The element will be built into DOM tree immediately
      """
      if elementclass: # build specific element
         name = elementclass.__name__.lower()             # get element's name       
         elem = self.__getattribute__(name)            # get element
         elem.buildnode(self)                          # build node
         self._built.append(elem)                      # mark as 'built'
         return

      for attr, elem in sorted(self.__dict__.items()): # for all attributes of Channel/Item instance
         if not attr.startswith('_'):                  # attribute's name doesn't start with '_'
            if elem and elem not in self._built:       # element is not None and has not been build
               elem.buildnode(self)                    # insert element in DOM tree
               self._built.append(elem)                # mark as 'built'


   def _createTextSection(self, data):
      """Create TextNode or CDATASection if self._cdata is True

      The functions creates CDATANode, if data contains markup characters
      Otherwise, it creates a TextNode

      Returns Node object 
      """
      if self._cdata:                  # required to format values with CDATA
         if self._pcdata.search(data): # markup character are present
            return self.document.createCDATASection(data)
         
      return self.document.createTextNode(data)
         


class RSSElement(metaclass=ABCMeta):
   """Abstract base class for classes that define RSS elements (except channel/item elements)"""
   @abstractmethod
   def buildnode(self, parent):
      """Build XML node(s) and attach them to the parent (RSSBaseElement object)"""
      pass


class RSSSingleElement(RSSElement):
   """Basic class for RSS Elements that have only a signle value to be defined"""
   def __init__(self, value, elementname = None):
      """Initialize RSS Element

      value       - element's value
      elementname - element's name; default value is self.__class__.__name__.lower()
      """
      self._value = str(value)
      self._elementname = elementname or self.__class__.__name__.lower()
      

   def buildnode(self, parent):
      elem = parent.document.createElement(self._elementname)
      elem.appendChild(parent._createTextSection(self._value))
      parent.root.appendChild(elem)



class Channel(RSSBaseElement):
   """RSS 2.0 Feed/Channel class"""
   def __init__(self, title, link, description, cdata = True, **optional):
      """Initialize RSS 2.0 Feed with a single channel inside it

      Most parameters could be passed as strings, but some of them
      require to be passed as an object of defined type (e.g. Cloud)
      These arguments will be marked with '(cls)' label (see below).
      The pubdate and lastbuilddate could also accept a datetime as a value. 
      Note, that ALL arguments could be passed as objects of their defined classes

      title       (str) - the title of the channel     
      link        (str) - the hyperlink to the channel 
      description (str) - describes the channel        
      cdata             - automatically quote fragments of elements' values containing markup characters

      Optional arguments (Channel elements):
      
      language           (str) - The language the channel is written in
      copyright          (str) - Copyright notice for content in the channel
      managingeditor     (str) - Email address for person responsible for editorial content
      webmaster	         (str) - Webmaster's email address
      pubdate	     (dt, str) - The publication date for the content in the channel
      lastbuilddate  (dt, str) - The last time the content of the channel changed
      generator          (str) - A string indicating the program used to generate the channel
      docs               (str) - A URL that points to the documentation for the format used in the RSS file
      ttl                (str) - Time To Live
      pics               (str) - The PICS rating for the channel
      category           (str) - Specifies one or more categories that the channel belongs to
      cloud              (cls) - Allows processes to register with a cloud to be notified of updates to the channel
      image              (cls) - Specifies a GIF, JPEG or PNG image that can be displayed with the channel
      textinput          (cls) - Specifies a text input box that can be displayed with the channel
      skiphours          (cls) - A hint for aggregators telling them which hours they can skip
      SkipDays           (cls) - A hint for aggregators telling them which days they can skip
      """
      RSSBaseElement.__init__(self, title, link, description, cdata, **optional) # initialize superclass

      # class-specific attributes, required for correct class work
      # these kind of attributes start with '_' character
      self._dom = xml.dom.minidom.getDOMImplementation()
      self._doc = self._dom.createDocument(None, 'rss', None)  # <rss 
      self._doc.documentElement.setAttribute('version', '2.0') #     version="2.0">
      
      self._root = self._doc.createElement('channel')   # <channel>...</channel>
      self._doc.documentElement.appendChild(self._root) 

      # build required elements, so they appear at the 'top' of the xml file
      self._build(Title)
      self._build(Link)
      self._build(Description)

      # Channel's optional elements      
      self._set(Language)       # set self.language if category is in optional arguments dict.
      self._set(Copyright)      # ... and so on for each optional elements
      self._set(ManagingEditor)
      self._set(WebMaster)
      self._set(PubDate)
      self._set(LastBuildDate)
      self._set(Generator)
      self._set(Docs)
      self._set(TTL)
      self._set(PICS)
      self._set(Category)
      self._set(Cloud)
      self._set(Image)
      self._set(TextInput)
      self._set(SkipHours)
      self._set(SkipDays)  

      self._build() # build DOM (document)
            

   def additem(self, item):
      """Add RSS item to the Channel

      item - Item object
      """
      self._root.appendChild(item.root)


   def toxml(self, encoding = 'utf-8', tostr = True):
      """Return xml document reprezentation of the Channel object

      encodint - text encoding (utf-8 by default)
      tostr    - automatically convert bytes sequence to string (True by default)
      """
      xml = self._doc.toxml(encoding)
      if tostr: xml = str(xml, encoding)
      return xml

   def toprettyxml(self, indent = '\t', newl = '\n', encoding = 'utf-8', tostr = True):
      """Return a pretty-printed version of the xml document. 

      indent   - the indentation string; default value is \t 
      newl     - the string emitted at the end of each line; default value is \n
      encodint - text encoding (utf-8 by default)
      tostr    - automatically convert bytes sequence to string (True by default)
      """
      xml = self._doc.toprettyxml(indent, newl, encoding)
      if tostr: xml = str(xml, encoding)
      return xml


   @property
   def document(self):
      return self._doc

   @property
   def root(self):
      return self._root



class Item(RSSBaseElement):
   """RSS 2.0 Item class"""
   def __init__(self, channel, title, link, description, **optional):
      """Initialize RSS 2.0 Item

      Most parameters could be passed as strings, but some of them
      require to be passed as an object of defined type (e.g. Enclosure)
      These arguments will be marked with '(cls)' label (see below).

      title         (str) - The title of the item
      link          (str) - The URL of the item
      description   (str) - The item synopsis

      Optional arguments (Item elements):

      author        (str) - Email address of the author of the item
      category      (str) - Specifies one or more categories that the item belongs to
      comments      (str) - URL of a page for comments relating to the item
      guid          (str) - A string that uniquely identifies the item
      pubdate   (dt, str) - The publication date of the item
      enclosure     (cls) - Describes a media object that is attached to the item
      source        (cls) - The RSS channel that the item came from
      """
      RSSBaseElement.__init__(self, title, link, description, **optional) # initialize superclass

      self._doc = channel.document
      self._root = self._doc.createElement('item')      

      # build required arguments 
      self._build(Title)
      self._build(Link)
      self._build(Description)

      # Item's optional elements
      self._set(Author)
      self._set(Category)
      self._set(Comments)
      self._set(Enclosure)
      self._set(GUID)
      self._set(PubDate)
      self._set(Source)

      self._build()


   @property
   def document(self):
      return self._doc

   @property
   def root(self):
      return self._root



class Title(RSSSingleElement):
   """The name of the channel/item"""
   pass


class Link(RSSSingleElement):
   """The URL to the HTML website corresponding to the channel or the URL of the item"""
   pass


class Description(RSSSingleElement):
   """Phrase or sentence describing the channel/item"""
   pass


class Author(RSSSingleElement):
   """Email address of the author of the item"""
   pass


class Comments(RSSSingleElement):
   """URL of a page for comments relating to the item

   Example: Comments('http://www.example.com/cgi-local/mt/mt-comments.cgi?entry_id=290')
   """
   pass


class Language(RSSSingleElement):
   """The language the channel is written in

   Example: Language('en-us')"""
   pass


class Copyright(RSSSingleElement):
   """Copyright notice for content in the channel

   Example: Copyright('Copyright 2009, Zaur Nasibov')"""
   pass


class Generator(RSSSingleElement):
   """A string indicating the program used to generate the channel

   Example: Generator('rss.py by Zaur Nasibov')"""
   pass


class Docs(RSSSingleElement):
   """A URL that points to the documentation for the format used in the RSS file

   Example: Docs('http://blogs.law.harvard.edu/tech/rss')"""
   pass


class TTL(RSSBaseElement):
   """Time To Live 

   It's a number of minutes that indicates how long a channel can be cached before refreshing from the source

   Example: TTL(60)
   """
   pass


class PICS(RSSSingleElement):
   """The PICS rating for the channel

   rss.py module does NOT support PICS rating generating. 
   The value should be generated outside of class's constructor
   """
   pass


class ManagingEditor(RSSSingleElement):
   """Email address for person responsible for editorial content

   Example: ManagingEditor('jsmith@example.com (John Smith)')
   """
   def __init__(self, value):
      RSSSingleElement.__init__(self, value, 'managingEditor')


class WebMaster(RSSSingleElement):
   """Email address for person responsible for technical issues relating to channel

   Example: WebMaster('jsmith@example.com (John Smith)')
   """
   def __init__(self, value):
      RSSSingleElement.__init__(self, value, 'webMaster')



class Category(RSSElement):
   """Specifies one or more categories that the channel/item belongs to

   Usage:
   Category(str, str, ..., (str, str), (str, str)... )
   Category(category1, category2, (category3, domain3), (category4, domain4))

   Example:
   Category('Development/Web development', 'Programming')
   Category(('RFC','http://www.example.com/rfc'))
   """
   def __init__(self, *categories):
      """Initialize Category object

      categories - one or more channel/item categories 
      """
      self._categories = []
      valid = True  # flag, indicates that arguments (*categories) are valid

      # create self._categories list with valid (category, domain) categories 
      for cat in categories:
         if type(cat) == str:
            self._categories.append((cat, None))    # create tuple with domain = None
         elif type(cat) == tuple and len(cat) == 2:
            self._categories.append(cat)
         else:
            raise RSSElemInitError(self)

   
   def buildnode(self, parent):
      doc = parent.document
      root = parent.root # channel or item element

      for cat in self._categories:
         category = cat[0]
         domain = cat[1]
         
         if len(category.strip()) > 0: # this is not an empty category
            elem = doc.createElement('category')
            if domain: elem.setAttribute('domain', domain) # add domain attribute
            elem.appendChild(parent._createTextSection(category))
            root.appendChild(elem)


class Enclosure(RSSElement):
   """Describes a media object that is attached to the item

   Usage:
   Enclosure(str, str|int, str)

   Example:
   Enclosure('http://www.example.com/example.mp3', 202400, 'audio/mpeg')
   """
   def __init__(self, url, length, enclosuretype):
      self._url = str(url)
      self._length = str(length)
      self._type = str(enclosuretype)
      
      if not self._length.isdecimal():
         raise RSSElemInitError(self)


   def buildnode(self, parent):
      elem = parent.document.createElement('enclosure')

      for attr, val in self.__dict__.items():  # for all attributes of Cloud instance
         if attr.startswith('_'):              # get object attributes that start with '_' character
            elem.setAttribute(attr[1:], val)   # attribute's name without leading '_'

      parent.root.appendChild(elem)            # append element to root      


class GUID(RSSElement):
   """A string that uniquely identifies the item

   Usage:
   Guid(str)
   Guid(str, bool)

   Example:
   Guid('http://example.com/2002/09/01.php#a2', False)
   """
   def __init__(self, guid, ispermalink = True):
      """Initialize GUID object

      guid         - stands for globally unique identifier, a string that uniquely identifies the item
      ispermalink -  if the value is False, the guid may not be assumed to be a url
      """
      self._guid = guid
      self._ispermalink = ispermalink

   
   def buildnode(self, parent):
      elem = parent.document.createElement('guid')

      if not self._ispermalink: elem.setAttribute('isPermaLink', 'false')
      elem.appendChild(parent._createTextSection(self._guid))
      parent.root.appendChild(elem)            
      

class Source(RSSElement):
   """The RSS channel that the item came from

   Usage:
   Source(str, str)

   Example:
   Source('Example channel', 'http://example.com/rss/examplechannel.xml')
   """
   def __init__(self, source, url):
      """Initialize Source object

      source - The name of the RSS channel that the item came from, derived from its <title>
      url    - links the item to the XMLization of the source
      """
      self._source = source
      self._url = url

   
   def buildnode(self, parent):
      elem = parent.document.createElement('source')

      elem.setAttribute('url', self._url)
      elem.appendChild(parent._createTextSection(self._source))
      parent.root.appendChild(elem)


class Cloud(RSSElement):
   """The <cloud> element class

   Usage:
   Cloud(str, str|int, str, str, str, [str])

   Example: Cloud('rpc.sys.com', '80', '/RPS2', 'myCloud.rssPleaseNotify')
   """
   def __init__(self, domain, port, path, regproc, protocol = 'xml-rpc'):
      # validate argument(s)
      port = str(port)
      if not (port.isdecimal()):
         raise RSSElemInitError(self)
      
      # validation OK
      self._domain = str(domain)
      self._port = port
      self._path = str(path)
      self._registerProcedure = str(regproc)
      self._protocol = str(protocol)


   def buildnode(self, parent):
      elem = parent.document.createElement('cloud')

      for attr, val in self.__dict__.items():  
         if attr.startswith('_'):              
            elem.setAttribute(attr[1:], val)   

      parent.root.appendChild(elem)            


class Image(RSSElement):
   """Specifies a GIF, JPEG or PNG image that can be displayed with the channel

   Usage: 
   Image(str, str, str, [str, [str|int, [str|int]]])

   Example: 
   Image('http://example.com/image.jpg', 'Example Feed', 'http://www.example.com')
   """
   def __init__(self, url, title, link, description = None, width = None, height = None):
      """Initialize Image object
      
      url         - is the URL of a GIF, JPEG or PNG image that represents the channel
      title       - is used in the ALT attribute of the HTML <img> tag; recommended value is channel's title
      link        - is the URL of the site, the image is a link to the site; recommended is channel's link
      description - contains text that is included in the TITLE attribute of the link 
      width       - indicates image's width in pixels, max. value is 144px; default value is 88px
      height      - indicates image's heigth in pixels, max. value is 400px; default value is 31px
      """
      # validation
      if width: width = int(width)
      if height: height = int(height)
      if (width != None and not 0 < width <= 144) or (height != None and not 0 < height <= 400):
         raise RSSElemInitError(self)

      self._url = str(url)
      self._title = str(title)
      self._link = str(link)
      self._description = description and str(description)
      self._width = width and str(width)
      self._height = height and str(height)

   
   def buildnode(self, parent):
      doc = parent.document
      imgelem = doc.createElement('image')
      
      for elem, val in self.__dict__.items():     # for all attributes of Image instance
         if elem.startswith('_') and val:         # get instance attributes that start with '_' character
            element = doc.createElement(elem[1:]) # don't include leading '_' here
            element.appendChild(parent._createTextSection(val))
            imgelem.appendChild(element)

      parent.root.appendChild(imgelem)


class PubDate(RSSElement):
   """The publication date for the content in the channel, or the item. 

   Usage:
   PubDate(datetime|str)

   Example: 
   PubDate('Sat, 14 June 2014 00:00:01 GMT')
   """
   def __init__(self, value):
      if type(value) == datetime:
         value = value.strftime('%a, %d %b %Y %H:%M:%S GMT')

      self._value = value

   def buildnode(self, parent):
      doc = parent.document

      element = doc.createElement('pubDate')
      element.appendChild(parent._createTextSection(self._value))
            
      parent.root.appendChild(element)


class LastBuildDate(RSSElement):
   """The last time the content of the channel changed
   
   Usage:
   LastBuildDate(datetime|str)

   Example: 
   LastBuildDate('Sun, 14 June 2009 01:39:47 GMT')
   """
   def __init__(self, value):
      if type(value) == datetime:
         value = value.strftime('%a, %d %B %Y, %H:%M:%S')

      self._value = value

   def buildnode(self, parent):
      doc = parent.document

      element = doc.createElement('lastBuildDate')
      element.appendChild(parent._createTextSection(self._value))
            
      parent.root.appendChild(element)


class TextInput(RSSElement):
   """Specifies a text input box that can be displayed with the channel

   Usage: 
   TextInput(title, description, name, link)

   Example: 
   TextInput('Submit', 'Reply to author', 'txtReply', 'http://example.com/rssreply.php')
   """
   def __init__(self, title, description, name, link):
      """Initialize TextInput object

      title - The label of the Submit button in the text input area
      description - Explains the text input area      
      name - The name of the text object in the text input area
      link - The URL of the CGI script that processes text input requests
      """
      self._title = str(title)
      self._description = str(description)
      self._name = str(name)
      self._link = str(link)


   def buildnode(self, parent):
      doc = parent.document
      tielem = doc.createElement('textInput')

      for elem, val in self.__dict__.items():  # for all attributes of textInput instance
         if elem.startswith('_'):              # get instance attributes that start with '_' character
            element = doc.createElement(elem[1:])
            element.appendChild(parent._createTextSection(val))
            tielem.appendChild(element)
            
      parent.root.appendChild(tielem)


class SkipHours(RSSElement):
   """A hint for aggregators telling them which hours they can skip

   Usage:
   SkipHours(int, int, ..., (int, int), (int, int), ...)
   SkipHours(hour, hour, ..., (hour_from, hour_to), (hour_from, hour_to), ...)
   
   Example:
   SkipHours((0,8), 18, (21,23)) # means skip hours 0,1...8,18,21...23
   """
   def __init__(self, *hours):
      """Initialize SkipHours object

      hours - hours to skip
      """
      self._hours = set() # empty set of hours
   
      # generate valid _hours set
      for hour in hours:
         if type(hour) == int:     # a single hour
            if 0 <= hour <= 23: 
               self._hours.add(hour)
            else:
               raise RSSElemInitError(self)
         elif type(hour) == tuple: # a range tuple
            if 0 <= hour[0] < hour[1] <= 23:
               for h in range(hour[0], hour[1] + 1):
                  self._hours.add(h)
            else:
               raise RSSElemInitError(self)

   def buildnode(self, parent):
      doc = parent.document
      skelem = doc.createElement('skipHours')
      
      for hour in self._hours:
         element = doc.createElement('hour')
         element.appendChild(parent._createTextSection(str(hour)))
         skelem.appendChild(element)

      parent.root.appendChild(skelem)


class SkipDays(RSSElement):
   """A hint for aggregators telling them which days they can skip

   Usage:
   SkipDays(int, int, ..., str, str, ..., (int, int), (int, int), ...)
   int:         day number [1-7]
   str:         day name (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday or Sunday)
   (int, int):  day number FROM, day number TO
   
   Example: 
   SkipDays(1, 'Wednesday', (5,7)) # means skip Monday, Wednesday, Friday, Saturday and Sunday
   """
   def __init__(self, *days):
      """Initialize SkipDays object

      days - days to skip; 
      """
      self._names = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
      self._days = set() # empty set of days' numbers
      
      # generate valid _days set
      for day in days:
         if type(day) == int:
            if 1 <= day <= 7: 
               self._days.add(day)
            else:
               raise RSSElemInitError(self)               
         elif type(day) == str:
            if day.title() in self._names: 
               self._days.add(self._names.index(day.title()) + 1)
            else:
               raise RSSElemInitError(self)
         elif type(day) == tuple:
            if 1 <= day[0] < day[1] <= 7:
               for d in range(day[0], day[1] + 1):
                  self._days.add(d)
            else:
               raise RSSElemInitError(self)


   def buildnode(self, parent):
      doc = parent.document
      skelem = doc.createElement('skipDays')
      
      for day in self._days:
         element = doc.createElement('day')
         element.appendChild(parent._createTextSection(self._names[day - 1]))
         skelem.appendChild(element)

      parent.root.appendChild(skelem)



class RSSError(Exception):
   """Base class for all rss.py errors"""
   def __init__(self, value):
      self.value = value

   def __str__(self):
      return repr(self.value)


class RSSElemInitError(RSSError):
   """RSS Element initialization error"""
   def __init__(self, rsselement):
      self.value = 'Error initializing {0}: wrong argument'.format(rsselement.__class__.__name__)
