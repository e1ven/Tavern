class Baseobj(object):
    """
    A base object for all Tavern objects.
    This will create some reasonable defaults in self that are really handy
    """

    def __init__(self,*args,**kwargs):
        import libtavern.server

        if 'slot' in kwargs and 'server' in kwargs:
            raise Exception("Baseobj","You can't have BOTH a 'slot' and 'server' argument")

        if 'slot' in kwargs:
            self.server = libtavern.server.Server(slot=kwargs['slot'])
            kwargs.pop('slot')
        elif 'server' in kwargs:
            self.server = kwargs['server']
            kwargs.pop('server')
        else:
            self.server = libtavern.server.Server()

        # Create a logger for this object, as a sublogger of server.
        self.logger = self.server.logger.getChild(__name__)
        self.logger.setLevel(self.server.logger.getEffectiveLevel())
        self.__init2__(*args,**kwargs)