import tornado.web

class ShowMessage(tornado.web.UIModule):
    """
    Show a Tavern Message.
    """
    def render(self, envelope,handler, childmap, top):
        return self.render_string(
            "UIModule-showmessage.html", envelope=envelope,handler=handler, top=top,childmap=childmap)

class ShowGlobalmenu(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler):
        return self.render_string(
            "UIModule-globalmenu.html",handler=handler)

class ShowMessagelist(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler):
        return self.render_string(
            "UIModule-messagelist.html",handler=handler)

class ShowPrivateMessagelist(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler,messages):
        return self.render_string(
            "UIModule-privatemessagelist.html",handler=handler,messages=messages)


class ShowUserdetails(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler,envelope,note=None):

        # Get the details on the guy we're looking up.
        trust = handler.user.gatherTrust(askingabout=envelope.dict['envelope']['local']['author']['pubkey'])
        note = handler.user.get_note(envelope.dict['envelope']['local']['author']['pubkey'])

        return self.render_string(
            "UIModule-userdetails.html",handler=handler,envelope=envelope,note=note,trust=trust)

class ShowAttachments(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler,envelope):
        return self.render_string(
            "UIModule-attachments.html",handler=handler,envelope=envelope)

