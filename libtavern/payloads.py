"""
This module contains the various Payloads that an envelope can contain.
Each Payload inherits from the BasePayload class, then overrides/extends
Validate and add_to_parent
"""
import libtavern.baseobj
import libtavern.key
import libtavern.utils
import libtavern.topic
import collections
import hashlib

class BasePayload(libtavern.baseobj.Baseobj):
    """This is the baseclass for all other Payloads. No message should stay in this state.
    envelope.register_payload should convert it to it's rightful type.
    """

    def __init2__(self, initialdict={}):
        self.dict = collections.OrderedDict(initialdict)

    def alphabetize(self, oldobj):
        """To ensure that we can break a message apart, and later put it back in the same order,
        all fiends in a message MUST be in alphabetical order."""

        # Recursively loop through all the keys/items
        # If we can sort them, do so, if not, just return it.

        if isinstance(oldobj, collections.Mapping):
            oldlist = oldobj.keys()
            newdict = collections.OrderedDict()

            for key in sorted(oldlist):
                newdict[key] = self.alphabetize(oldobj[key])
            return newdict

        elif isinstance(oldobj, collections.Sequence) and not isinstance(oldobj, str):
            newlist = []

            # If this is an array of collections.OrderedDicts, for example, we can't sort them.
            # So leave them as they are.
            try:
                oldlist = sorted(oldobj)
            except TypeError:
                oldlist = oldobj

            for row in oldlist:
                newlist.append(self.alphabetize(row))
            return newlist

        else:
            return oldobj

    def format(self):
        """
        Format a Payload to spec.
        """
        self.dict = self.alphabetize(self.dict)

    def hash(self):
        """
        Returns a hashed version of the payload JSON, used as the contentid.
        :return str: hashed version of payload JSON.
        """
        h = hashlib.sha512()
        h.update(self.text().encode('utf-8'))
        return h.hexdigest()

    def text(self):
        """
        Returns a JSON version of the formatted payload object.
        :return str: JSON of the payload.
        """
        self.format()
        return libtavern.utils.to_json(self.dict)

    @property
    def validates(self):
        """
        Does this obj do the minimum to be considered a payload at all?
        This should always be overridden, but may be called by children.
        :return True/False: Is this a valid payload
        """

        self.alphabetize(self.dict)


    def add_to_parent(self,parent):
        """ Called on a child envelope, so it can store it's id in it's parent.
        For example, if we received a message reply, reply.add_to_parent would mark it's id in the original
        :param Envelope parent: The original envelope which this is modifying
        """
        self.logger.debug(" I am :: " + self.dict['envelope']['local']['payload_sha512'])
        self.logger.debug(" Adding a cite on my parent :: " + parent.dict['envelope']['local']['payload_sha512'])
        parent.add_cite(new.dict['envelope']['local']['payload_sha512'])
        self.add_ancestor(new.dict['envelope']['payload']['regarding'])

class Message(BasePayload):
    """
    A message is a post that is designed to be shared with the world.
    These would be similar to a Usenet post or reddit comment.
    Note - Both the original message, and any replies, are both Messages.
    """

    @property
    def validates(self):
        """
        :return: True/False - Does this follow the rules of a message?
        """
        if not BasePayload(self.dict).validates:
            self.server.logger.debug("Super does not Validate")
            return False
        if 'subject' not in self.dict:
            self.server.logger.debug("No subject")
            return False
        if 'body' not in self.dict:
            self.server.logger.debug("No Body")
            return False
        if 'topic' not in self.dict:
            self.server.logger.debug("No Topic")
            return False
        if 'formatting' not in self.dict:
            self.server.logger.debug("No Formatting")
            return False
        if self.dict['formatting'] not in ['markdown', 'plaintext']:
            self.server.logger.debug("Formatting not in pre-approved list")
            return False
        if len(self.dict['topic']) > 200:
            self.server.logger.debug("Topic too long")
            return False
        if len(self.dict['subject']) > 200:
            self.server.logger.debug("Subject too long")
            return False

        # If this is a reply, verify the original is also a 'message'
        if 'regarding' in self.dict:
            e = Envelope(server=self.server)
            if e.loadmongo(self.dict['regarding']):
                if e.dict['envelope']['payload']['class'] != 'message':
                    self.server.logger.debug("This envelope was trying to modify something that was not a message.")
                    return False

        return True


class PrivateMessage(BasePayload):

    def validates(self):
        if not BasePayload(self.dict).validates():
            self.server.logger.debug("Super does not Validate")
            return False
        if 'to' not in self.dict:
            self.server.logger.debug("No 'to' field")
            return False
        # if 'topic' in self.dict:
        #     self.server.logger.debug("Topic not allowed in privmessage.")
        #     return False
        return True

class Rating(BasePayload):

    def validates(self):
        if not BasePayload(self.dict).validates():
            self.server.logger.debug("Super fails")
            return False
        if 'rating' not in self.dict:
            self.server.logger.debug("No rating number")
            return False
        if self.dict['rating'] not in [-1, 0, 1]:
            self.server.logger.debug(
                "Evelope ratings must be either -1, 1, or 0.")
            return False

        return True

    def add_to_parent(self,parent):
        """
        If we receive an message rating, this message will note that rating in the original message.
        :param Envelope parent: The original message which we rated.
        """
        super().add_to_parent(parent)

        # Note the author of the message we rated in the Rating.
        # This lets us search later, to see how people feel about us ;)
        self.dict['envelope']['local']['regarding_author'] = parent.dict['envelope']['payload']['author']
        self.saveMongo()

        return True

class UserTrust(BasePayload):

    def validates(self):
        if not BasePayload(self.dict).validates():
            return False
        if 'trusted_pubkey' not in self.dict:
            self.server.logger.debug("No trusted_pubkey to set trust for.")
            return False
        if self.dict['trust'] not in [-100, 0, 100]:
            self.server.logger.debug(
                "Message ratings must be either -100, 0, or 100")
            return False
        if 'topic' not in self.dict:
            self.server.logger.debug(
                "User trust must be per topic. Please include a topic.")
            return False
        return True

class MessageRevision(BasePayload):
    def validates(self):
        if not BasePayload(self.dict).validates():
            self.server.logger.debug("Super does not Validate")
            return False
        if not 'regarding' in self.dict:
            self.server.logger.debug(
                "Message Revisions must refer to an original message.")
            return False

        # See if we have the original. If so, is the right type?
        e = Envelope()
        if e.loadmongo(self.dict['regarding']):
            print("We have the original message this revision refers to")
            if e.dict['envelope']['payload']['class'] != 'message':
                print("Message Revisions must refer to a message.")
                return False
        return True

    def add_to_parent(self,parent):
        """
        If we receive an edit to an existing message, this method will let us note that in the original.
        :param Envelope parent: The original envelope which was edited.
        """

        super().add_to_parent(parent)

        if not 'edits' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['edits'] = []

        # Don't add the same edit twice.
        if self.payload.hash in original.dict['envelope']['local']['edits']:
            self.server.logger.debug("We've already stored this edit.")
            return False

        # Ensure the edit is by the same author as the original.
        # Do this here, rather than in validate, since we can receive messages in either order.
        if self.dict['envelope']['local']['author']['pubkey'] != parent.dict['envelope']['local']['author']['pubkey']:
            self.server.logger.debug("Invalid Revision. Author pubkey must match original message.")
            return False

        self.dict['envelope']['local']['edits'].append(newmessage.dict)

        # Order messages by Priority - Each edit should increase the priority by one.
        # Depending on which messages a server had received, they might not always do so, however.
        # If this comes up, use the date received as a tie breaker.
        self.dict['envelope']['local']['edits'].sort(
            key=lambda e: (e['envelope']['local']['priority'],(e['envelope']['local']['time_added'])))
        self.saveMongo()


