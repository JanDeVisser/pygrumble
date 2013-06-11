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

# TODO:
#  Run actions in Tx
#  If action returns status, and this is the first action in the list to do so,
#    apply status
#

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
            a(process = process, status = self)

    def removed(self, process):
        for a in self._on_removed:
            a(process = process, status = self)

class Event(object):
    def __init__(self, action):
        self._action = action

class StatusEvent(Event):
    pass

class OnAdd(StatusEvent):
    def __call__(self, status):
        status.on_added(self._action)

class OnRemove(StatusEvent):
    def __call__(self, status):
        status.on_removed(self._action)

class ProcessEvent(Event):
    pass

class OnStarted(ProcessEvent):
    def __call__(self, process):
        process.on_started(self._action)

class OnStopped(ProcessEvent):
    def __call__(self, process):
        process.on_stopped(self._action)

class AddedStatus(grumble.Model):
    name = grumble.TextProperty()

class Action(object):
    pass

class ProcessAction(Action):
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            self._target = args[0]
        elif "process" in kwargs:
            self._target = kwargs["process"]
        else:
            self._target = None

    def get_target(self, ctx):
        if not self._target:
            return ctx
        else:
            return ctx.resolve(self._target)

class Start(ProcessAction):
    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target.start()

class Stop(ProcessAction):
    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target.stop()

class Transition(ProcessAction):
    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        process.stop()
        if target:
            target.start()

class Process(object):
    def __init__(self, *args, **kwargs):
        # TODO Grab parent process
        pass

    def __call__(self, cls):
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

        def on_started(self, action):
            self._on_started += action
        cls.on_started = on_started

        def on_stopped(self, action):
            self._on_stopped = []
        cls.on_stopped = on_stopped

        def start(self):
            if self.starttime is None:
                self.starttime = datetime.datetime.now()
                self.put()
                for a in self._on_started:
                    a(process = self)
        cls.start = start

        def stop(self):
            if self.starttime is not None and self.finishtime is None:
                self.finishtime = datetime.datetime.now()
                self.put()
                for a in self._on_stopped:
                    a(process = self)
        cls.stop = stop

        def add_status(self, status):
            status = status.name() if isinstance(status, Status) else status
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
            status = status.name() if isinstance(status, Status) else status
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

        def resolve(self, path):
            # TODO Implement
            return self
        cls.resolve = resolve

        return cls
