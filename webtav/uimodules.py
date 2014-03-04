import tornado.web
import libtavern.envelope


class ShowMessage(tornado.web.UIModule):

    """
    Show a Tavern Message.
    """
    def render(self,envelope, top):

        messagerating = self.handler.user.getRatings(postInQuestion=envelope.dict['envelope']['local']['payload_sha512'])
        note = self.handler.user.get_note(noteabout=envelope.dict['envelope']['local']['author']['pubkey'])
        if envelope.dict['envelope']['local'].get('medialink',None):
            medialink = self.handler.server.serversettings.settings['webtav']['downloads_url'] + envelope.dict['envelope']['local']['medialink']
        else:
            medialink = self.handler.server.url_for(envelope)
        if top:
            avatarsize = 80
        else:
            avatarsize = 40

        # Retrieve the children as objects.
        if 'citedby' in envelope.dict['envelope']['local']:
            envelope.dict['envelope']['local']['citeenvs'] = []
            for cite in envelope.dict['envelope']['local']['citedby']:
                e = libtavern.envelope.Envelope()
                e.loadmongo(cite)
                envelope.dict['envelope']['local']['citeenvs'].append(e)

        return self.render_string(
            "UIModule-showmessage.html", envelope=envelope, top=top,avatarsize=avatarsize,medialink=medialink,messagerating=messagerating,note=note)

class ShowGlobalmenu(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self):
        return self.render_string(
            "UIModule-globalmenu.html")

class ShowMessagelist(tornado.web.UIModule):
    """
    Show the Message List (generally the middle pane)
    """
    def render(self):

        # Ensure we messages
        if not self.handler.messages:
            self.handler.messages = self.handler.topic.messages(maxposts=self.handler.user.maxposts,before=self.handler.before,after=self.handler.after,include_replies=False)

        if not hasattr(self.handler,'specialtopic'):
            self.handler.specialtopic = False

        # Calculate the forward/back buttons
        show_older = False
        show_newer = False
        if self.handler.messages:
            if self.handler.topic.count(before=self.handler.messages[0].dict['envelope']['local']['time_added'],include_replies=False):
                show_older = True
            if self.handler.topic.count(after=self.handler.messages[-1].dict['envelope']['local']['time_added'],include_replies=False):
                show_newer = True

        return self.render_string(
            "UIModule-messagelist.html",show_older=show_older,show_newer=show_newer)

class ShowPrivateMessagelist(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self,messages):
        return self.render_string(
            "UIModule-privatemessagelist.html",messages=messages)


class ShowUserdetails(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self,envelope,note=None):

        # Get the details on the guy we're looking up.
        trust = self.handler.user.gatherTrust(askingabout=envelope.dict['envelope']['local']['author']['pubkey'])
        note = self.handler.user.get_note(envelope.dict['envelope']['local']['author']['pubkey'])

        return self.render_string(
            "UIModule-userdetails.html",envelope=envelope,note=note,trust=trust)

class ShowAttachments(tornado.web.UIModule):
    """
    Show the Global Menu (generally the first pane on the left)
    """
    def render(self,envelope):
        return self.render_string(
            "UIModule-attachments.html",envelope=envelope)

class xsrf_form_html(tornado.web.UIModule):
    """
    Includes the XSRF token as a hidden variable.
    This overwrites the default tornado xsrf_form_html, with a version that includes via SSI.
    """
    def render(self):
        return """<input type="hidden" name="_xsrf" value="<!--# echo var='xsrftoken' default='no' -->"/>"""
