from pcloud.dummyprotocol import PCloudDummyConnection
from pcloud.jsonprotocol import PCloudJSONConnection
from pcloud.binaryprotocol import PCloudBinaryConnection


class TestProtocol(object):
    name = "test"
    endpoint = "http://localhost:5023/"
    connection = PCloudDummyConnection


class JsonAPIProtocol(object):
    name = "api"
    endpoint = "https://api.pcloud.com/"
    connection = PCloudJSONConnection


class JsonEAPIProtocol(object):
    name = "eapi"
    endpoint = "https://eapi.pcloud.com/"
    connection = PCloudJSONConnection


class BinAPIProtocol(object):
    name = "binapi"
    endpoint = "https://binapi.pcloud.com/"
    connection = PCloudBinaryConnection


class BinEAPIProtocol(object):
    name = "bineapi"
    endpoint = "https://bineapi.pcloud.com/"
    connection = PCloudBinaryConnection


class NearestProtocol(object):
    name = "nearest"
    endpoint = ""
    connection = PCloudJSONConnection
