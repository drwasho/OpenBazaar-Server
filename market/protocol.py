__author__ = 'chris'
"""
This protocol class handles all direct (non-kademlia) messages between nodes.
All of the messages between a buyer and a vendor's store can be found here.
"""

from zope.interface import implements

from rpcudp import RPCProtocol
from interfaces import MessageProcessor
from log import Logger

from protos.message import GET_CONTRACT, GET_IMAGE, GET_PROFILE, GET_LISTINGS, GET_METADATA

from db.datastore import HashMap

from market.profile import Profile

from protos.objects import Metadata

class MarketProtocol(RPCProtocol):
    implements(MessageProcessor)

    def __init__(self, node_proto, router, signing_key):
        self.router = router
        RPCProtocol.__init__(self, node_proto, router)
        self.log = Logger(system=self)
        self.handled_commands = [GET_CONTRACT, GET_IMAGE, GET_PROFILE, GET_LISTINGS, GET_METADATA]
        self.multiplexer = None
        self.hashmap = HashMap()
        self.signing_key = signing_key

    def connect_multiplexer(self, multiplexer):
        self.multiplexer = multiplexer

    def rpc_get_contract(self, sender, contract_hash):
        self.log.info("Looking up contract ID %s" % contract_hash.encode('hex'))
        self.router.addContact(sender)
        try:
            with open(self.hashmap.get_file(contract_hash), "r") as file:
                contract = file.read()
            return [contract]
        except:
            return ["None"]

    def rpc_get_image(self, sender, image_hash):
        self.log.info("Looking up image with hash %s" % image_hash.encode('hex'))
        self.router.addContact(sender)
        try:
            with open(self.hashmap.get_file(image_hash), "r") as file:
                image = file.read()
            return [image]
        except:
            return ["None"]

    def rpc_get_profile(self, sender):
        self.log.info("Fetching profile")
        self.router.addContact(sender)
        try:
            proto = Profile().get(True)
            return [proto, self.signing_key.sign(proto)[:64]]
        except Exception:
            return ["None"]

    def rpc_get_metadata(self, sender):
        self.log.info("Fetching metadata")
        self.router.addContact(sender)
        try:
            proto = Profile().get(False)
            m = Metadata()
            m.name = proto.name
            m.handle = proto.handle
            m.avatar_hash = proto.avatar_hash
            return [m.SerializeToString(), self.signing_key.sign(m.SerializeToString())[:64]]
        except Exception:
            return ["None"]

    def callGetContract(self, nodeToAsk, contract_hash):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.get_contract(address, contract_hash)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def callGetImage(self, nodeToAsk, image_hash):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.get_image(address, image_hash)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def callGetProfile(self, nodeToAsk):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.get_profile(address)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def callGetMetadata(self, nodeToAsk):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.get_metadata(address)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def handleCallResponse(self, result, node):
        """
        If we get a response, add the node to the routing table.  If
        we get no response, make sure it's removed from the routing table.
        """
        if result[0]:
            self.log.info("got response from %s, adding to router" % node)
            self.router.addContact(node)
        else:
            self.log.debug("no response from %s, removing from router" % node)
            self.router.removeContact(node)
        return result

    def __iter__(self):
        return iter(self.handled_commands)
