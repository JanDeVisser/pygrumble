import datetime
import gripe
import gripe.smtp
import grumble
import grit
import grit.auth
import grit.handlers
import grit.role
import grizzle

logger = gripe.get_logger("grudge")


class Trigger(object):
    pass

class ProcessStarted(Trigger):
    pass

class ProcessFinished(Trigger):
    pass

class StatusAdded(Trigger):
    pass

class StatusRemoved(Trigger):
    pass

class Action(object):
    def start(self):
        pass

    @classmethod
    def execute(cls, owner):
        action = cls.create_action(owner) \
            if hasattr(cls, "create_action") and callable(cls.create_action) \
            else cls(owner)
        action.start()
        return action

class Start(Action):
    pass

class Stop(Action):
    pass

class AddStatus(Action):
    pass

class RemoveStatus(Action):
    pass

class WorkItem(Action, grumble.Model):
    title = grumble.TextProperty()
    start = grumble.DateTimeProperty(auto_now_add = True)
    finish = grumble.DateTimeProperty()

    def start(self):
        self.put()
        
    def add_status(self, name):

    @classmethod
    def create_action(cls, owner = None):
        wi = cls(parent = owner)
        return wi

class Status(grumble.Model):
    name = grumble.TextProperty(is_key = True)

class ProcessDef(object):
    def __init__(self, cls):
        self.impl = cls


_process_registry = {}

def process(cls):
    _process_registry[cls.__name__] = ProcessDef(cls)
    return cls

