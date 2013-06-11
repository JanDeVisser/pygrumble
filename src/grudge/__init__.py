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

def Status(object):
    def __init__(self):
        self._name = name
        self._on_added = []
        self._on_removed = []
        
    def name(self, value = None):
        if value:
            self._name = value
        return self._name
    
    def on_added(self, action):
        self._on_added += action
        
    def on_removed(self, action):
        self._on_removed = []
        
    def added(self, process):
        for a in self._on_added:
            a.execute(process = process, status = self)
    
    def removed(self, process):
        for a in self._on_removed:
            a.execute(process = process, status = self)

class Event(object):
    pass

class StatusEvent(Event):
    def __init__(self, action):
        self._action = action    
    
class OnAdd(StatusEvent):
    def __call__(self, status):
        status.on_added(self._action)

class OnRemove(StatusEvent):
    def __call__(self, status):
        status.on_removed(self._action)

class AddedStatus(grumble.Model):
    name = grumble.TextProperty()


def Process(cls):
    grumble.ModelMetaClass.add_property(cls, "title", grumble.TextProperty())
    grumble.ModelMetaClass.add_property(cls, "starttime", grumble.DateTimeProperty())
    grumble.ModelMetaClass.add_property(cls, "finishtime", grumble.DateTimeProperty())
    cls._statuses = {}
    for (propname, propdef) in cls.__dict__:
        if isinstance(propdef, Status):
            propdef.name(propname)
            cls._statuses[propname] = propdef
    cls._on_started = []
    cls._on_stopped = []

    def start(self):
        if self.starttime is None:
            self.starttime = datetime.datetime.now()
            self.put()
            for a in self._on_started:
                a.execute(process = self)
    cls.start = start
            
    def stop(self):
        if self.starttime is not None and self.finishtime is None:
            self.finishtime = datetime.datetime.now()
            self.put()
            for a in self._on_stopped:
                a.execute(process = self)
    cls.stop = stop
            
    def add_status(self, status):
        assert status in self._statuses, "Cannot add status %s to process %s" % (status, self.__class__.__name__)
        statusdef = self._statuses[status]
        added = None
        for s in AddedStatus.query(ancestor = self):
            if s.name == status:
                added = s
        if added is None:
            added = AddedStatus(name = status, parent = self)
            added.put()
            statusdef.added(self)
        return added
    cls.add_status = add_status
    
    def remove_status(self, status):
        assert status in self._statuses, "Cannot remove status %s from process %s" % (status, self.__class__.__name__)
        statusdef = self._statuses[status]
        remove = None
        for s in AddedStatus.query(ancestor = self):
            if s.name == status:
                remove = s
        if remove is not None:
            grumble.delete(remove)
            statusdef.removed(self)
        return
    cls.remove_status = remove_status
    
    return cls

class Trigger(object):
    pass

class ProcessStarted(Trigger):
    pass

class ProcessFinished(Trigger):
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
    statuses = grumble.ListProperty()

    def start(self):
        self.put()
        
    def add_status(self, name):
        pass
        
    @classmethod
    def create_action(cls, owner = None):
        wi = cls(parent = owner)
        return wi

