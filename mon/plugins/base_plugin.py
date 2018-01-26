NAMESPACE = "node"


class BasePlugin(object):
    def __init__(self, config):
        print self.__class__.__name__, "inited"
        pass

    def collect(self):
        pass

    def start_update(self):
        pass
