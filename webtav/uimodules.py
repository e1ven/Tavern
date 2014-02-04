import tornado.web
import libtavern.utils as utils

class ShowMessage(tornado.web.UIModule):
    """
    Show a Tavern Message.
    """
    def render(self, envelope,handler, childmap, top):
        permalink = handler.server.url_for(envelope=envelope)
        messagerating = handler.user.getRatings(postInQuestion=envelope.dict['envelope']['local']['payload_sha512'])
        note = handler.user.get_note(noteabout=envelope.dict['envelope']['local']['author']['pubkey'])
        if envelope.dict['envelope']['local'].get('medialink',None):
            print( envelope.dict['envelope']['local']['medialink'])
            medialink = handler.server.serversettings.settings['webtav']['downloads_url'] + envelope.dict['envelope']['local']['medialink']
        else:
            medialink = permalink
        if top:
            avatarsize = 80
        else:
            avatarsize = 40

        return self.render_string(
            "UIModule-showmessage.html", envelope=envelope,handler=handler, top=top,childmap=childmap,avatarsize=avatarsize,medialink=medialink,permalink=permalink,messagerating=messagerating,note=note,utils=utils)

class ShowGlobalmenu(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self, handler):
        return self.render_string(
            "UIModule-globalmenu.html",handler=handler)

class ShowMessagelist(tornado.web.UIModule):
    """
    Show the Message List (generally the middle pane)
    """
    def render(self, handler):

        _ = handler.topicfilter.set_topic(handler.topic)
        subjects = handler.topicfilter.messages(maxposts=handler.user.maxposts,before=handler.before,after=handler.after,include_replies=False)

        # Calculate the forward/back buttons
        if subjects:
            if handler.topicfilter.count(before=subjects[0].dict['envelope']['local']['time_added']):
                show_older = True
            else:
                show_older = False
            if handler.topicfilter.count(after=subjects[-1].dict['envelope']['local']['time_added']):
                show_newer = True
            else:
                show_newer = False

        return self.render_string(
            "UIModule-messagelist.html",handler=handler,subjects=subjects,show_older=show_older,show_newer=show_newer)

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

