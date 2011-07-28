import asyncmongo
import tornado.web
import pprint
from tornado.options import define, options
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import pymongo
from pymongo import Connection
connection = Connection()
mongo = Connection('localhost', 27017) 
db = connection['test']

class Handler(tornado.web.RequestHandler):
    def get(self):
        db.envelopes.find({}, limit=1)
        # or
        # conn = self.db.connection(collectionname="...", dbname="...")
        # conn.find(..., callback=self._on_response)
        print "foo"
        print "April"
        self.write("Initial Method!")
        # self.render('template', full_name=respose['full_name'])
        self.write("Joe")
        # self.write(response[0]['envelope'])
        print "Superman"
        self.finish()
        
define("port", default=8888, help="run on the given port", type=int)
def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", Handler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
