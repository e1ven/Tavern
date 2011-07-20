import asyncmongo
import tornado.web
import pprint
from tornado.options import define, options
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web



class Handler(tornado.web.RequestHandler):
    @property
    def db(self):
        if not hasattr(self, '_db'):
            self._db = asyncmongo.Client(pool_id='mydb', host='127.0.0.1', port=27017, maxcached=10, maxconnections=50, dbname='test')
        return self._db

    @tornado.web.asynchronous
    def get(self):
        self.db.envelopes.find({}, limit=1, callback=self._on_response)
        # or
        # conn = self.db.connection(collectionname="...", dbname="...")
        # conn.find(..., callback=self._on_response)
        print "foo"
        print "April"
        self.write("Initial Method!")
        
    def _on_response(self, response, error):
        if error:
            raise tornado.web.HTTPError(500)
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