import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def recursion(self,count):
        return self.render_string('test.html',
            count=count,
            recursion=self.recursion)
            
    def get(self):
        self.write(self.render_string('test.html',count=1,recursion=self.recursion))

application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
    
    # {uper.write(self.render_string('test.html',title="BLAH!",count=count + 1))}}
	