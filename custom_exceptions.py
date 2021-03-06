## @package PyHoot.custom_exceptions
# Special exceptions for the project
## @file custom_exceptions.py Implementation of @ref PyHoot.custom_exceptions


class Disconnect(RuntimeError):
    """Represent an error that happend when someone disconnects"""

    def __init__(self):
        """initialization"""
        super(Disconnect, self).__init__("Disconnect")


class CorruptXML(RuntimeError):
    """Represent an error that happend when someone tries to use a Corrupt test
    file"""

    def __init__(self, message):
        """initialization"""
        super(CorruptXML, self).__init__("Corrupt XML: %s" % message)
