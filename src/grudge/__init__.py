import datetime
import gripe
import gripe.db
import gripe.smtp
import grumble

import threading
import Queue

logger = gripe.get_logger("grudge")

# TODO:
#  If action returns status, and this is the first action in the list to do so,
#    apply status
#

class Worker(object):
    def __init__(self, q, ix):
        self._ix = ix
        self._queue = q

    def __call__(self):
        while True:
            action = self._queue.get()
            assert action, "Message Queue takes sequence as action"
            a = action[0]
            if a:
                args = action[1] if len(action) > 1 else []
                args = args or []
                kwargs = action[2] if len(action) > 2 else {}
                kwargs = kwargs or {}
                logger.debug("Worker %s: handling(%s, %s, %s)", self._ix,
                    a, args, kwargs)
                with gripe.db.Tx.begin():
                    ret = a(*args, **kwargs)
                    if isinstance(ret, (basestring, Status)) and "process" in kwargs:
                        process = kwargs["process"]()
                        s = process.get_status(ret) \
                                if isinstance(ret, basestring) \
                                else ret
                        if isinstance(s, Status):
                            process.add_status(s)
            self._queue.task_done()


class MessageQueue(object):
    def __init__(self, name, workers):
        self._q = Queue.Queue()
        self._name = name
        for i in range(workers):
            t = threading.Thread(target = Worker(self._q, i))
            t.daemon = True
            t.setName("Message Q %s Worker thread %s" % (name, i))
            t.start()

    def put_action(self, action, *args, **kwargs):
        logger.debug("MQ .put(%s)", action.__class__.__name__)
        self._q.put((action, args, kwargs))

    def join(self):
        self._q.join()

_queue = MessageQueue("Grudge WF", 5)

class Status(object):
    def __init__(self, name = None, label = None):
        self._name = name or self.__class__.__name__
        self._label = label
        self._on_added = []
        self._on_removed = []

    def name(self, value = None):
        if value:
            self._name = value
        return self._name

    def label(self, value = None):
        if value:
            self._label = value
        return self._label

    def __str__(self):
        return "S(%s)" % self.label() or self.name()

    def __repr__(self):
        return self.__str__()

    def on_added(self, action):
        self._on_added.append(action)

    def on_removed(self, action):
        self._on_removed.append(action)

    def added(self, process):
        for a in self._on_added:
            _queue.put_action(a, process = grumble.Key(process), status = self)

    def removed(self, process):
        for a in self._on_removed:
            _queue.put_action(a, process = grumble.Key(process), status = self)

#
# -------------------------------------------------------------------------
#   A C T I O N S
# -------------------------------------------------------------------------
#

class Action(object):
    def __str__(self):
        return self.__class__.__name__

#
# -------------------------------------------------------------------------
#   P r o c e s s  A c t i o n s
#
#   Actions that change the state of a process - Start, Stop, Add status
# -------------------------------------------------------------------------
#

class ProcessAction(Action):
    def __init__(self, *args, **kwargs):
        self.set_process(*args, **kwargs)

    def set_process(self, *args, **kwargs):
        if len(args) > 0:
            self._target = args[0]
        elif "process" in kwargs:
            self._target = kwargs["process"]
        else:
            self._target = None
        if self._target:
            self._target = grumble.Key(self._target)

    def get_target(self, ctx):
        if not self._target:
            return ctx()
        else:
            return ctx().resolve_process(self._target)

class Start(ProcessAction):
    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target().start()

class Stop(ProcessAction):
    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target().stop()

class Transition(ProcessAction):
    def __str__(self):
        return "(--> %s)" % self._target

    def __call__(self, **kwargs):
        process = kwargs.get("process")
        logger.debug("Transition %s to %s", process, self._target)
        target = self.get_target(process)
        process().stop()
        if target:
            target().start()

class StatusAction(ProcessAction):
    def __init__(self, *args, **kwargs):
        logger.debug("Add(%s, %s)", args, kwargs)
        self.set_process(*(args[1:] if len(args) > 1 else ()), **kwargs)
        if len(args) > 0:
            self._status = args[0]
        elif "status" in kwargs:
            self._status = kwargs["status"]
        else:
            self._status = None

class Add(StatusAction):
    def __str__(self):
        return "(+ %s)" % self._status

    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target().add_status(self._status)

class Remove(StatusAction):
    def __str__(self):
        return "(- %s)" % self._status

    def __call__(self, **kwargs):
        process = kwargs.get("process")
        target = self.get_target(process)
        if target:
            target().remove_status(self._status)

#
# -------------------------------------------------------------------------
#   G e n e r a l  A c t i o n s
# -------------------------------------------------------------------------
#

class Invoke(Action):
    def __init__(self, *args, **kwargs):
        self._args = []
        if args:
            self._method = args[0]
            if len(args) > 1:
                self._args.extend[args[1:]]
        if "method" in kwargs:
            self._method = kwargs["method"]
        if "args" in kwargs:
            self._args.extend(kwargs["args"])
        self._kwargs = kwargs["kwargs"] if "kwargs" in kwargs else {}
        assert self._method, "Method must be specified for Invoke action"
        if not self._method.endswith("()"):
            self._method += "()"

    def __str__(self):
        return "(::%s)" % self._method

    def __call__(self, **kwargs):
        process = kwargs.get("process")
        logger.debug("Invoking %s", self._method)
        return process().resolve_attribute(self._method, self._args, self._kwargs)


class SendMail(Action):
    def __init__(self, **kwargs):
        assert "recipients" in kwargs, "Recipients must be specified for SendMail action"
        assert "text" in kwargs, "Text must be specified for SendMail action"
        self._recipients = kwargs.get("recipients")
        self._subject = kwargs.get("subject")
        self._text = kwargs["text"]
        self._status = kwargs.get("status")
        self._headers = kwargs.get("headers", {})
        self._ctx = kwargs.get("context")

    def __str__(self):
        return "mailto:%s" % self._recipients

    def _ctx_factory(self, msg, ctx):
        process = ctx["process"]()
        msg.recipients(process.resolve_attribute(self._recipients[1:])
            if process and self._recipients and self._recipients.startswith("@")
            else self._recipients)
        msg.subject(process.resolve_attribute(self._subject[1:])
            if process and self._subject and self._subject.startswith("@")
            else self._subject)
        if self._headers:
            for header in self._headers:
                val = self._headers[header]
                if process and val.startswith("@"):
                    val = process().resolve_attribute(val[1:])
                logger.debug("Adding header %s: %s", header, val)
                msg.set_header(header, val)
        if self._ctx is not None:
            ctx_obj = process().resolve_attribute(self._ctx)
            if callable(ctx_obj):
                ctx = ctx_obj(msg, ctx)
            elif ctx is not None:
                ctx.update(ctx_obj)
        logger.debug("Sending email\nTo: %s\nSubject: %s", msg.recipients(), msg.subject())
        return ctx

    def __call__(self, **kwargs):
        process = kwargs.get("process")
        text = process().resolve_attribute(self._text[1:]) \
            if process and self._text.startswith("@") \
            else self._text
        msg = None
        if text.startswith("&"):
            msg = gripe.smtp.TemplateMailMessage(text[1:])
        else:
            msg = gripe.smtp.MailMessage()
            msg.body(text)
        msg.context_factory(self._ctx_factory)
        msg.send({"process": process()})
        return self._status

#
# -------------------------------------------------------------------------
#   E V E N T S
# -------------------------------------------------------------------------
#

class Event(object):
    def __init__(self, *args, **kwargs):
        assert len(args), "Event must specify an action"
        if len(args) == 1 and isinstance(args[0], Action):
            action = args[0]
        else:
            action = Invoke(*args, **kwargs)
        self._action = action

#
# -------------------------------------------------------------------------
#   S T A T U S  E V E N T S
# -------------------------------------------------------------------------
#

class StatusEvent(Event):
    def __init__(self, status, *args, **kwargs):
        super(StatusEvent, self).__init__(*args, **kwargs)
        self._status = status

    def __str__(self):
        return "StatusEvent %s for status %s" % (self.__class__.__name__, self._status)

class OnAdd(StatusEvent):
    def __call__(self, process):
        logger.debug("Calling decorator %s", self)
        s = process().get_status(self._status)
        s.on_added(self._action)
        return process

class OnRemove(StatusEvent):
    def __call__(self, process):
        logger.debug("Calling decorator %s", self)
        s = process().get_status(self._status)
        s.on_removed(self._action)
        return process

#
# -------------------------------------------------------------------------
#   P R O C E S S  E V E N T S
# -------------------------------------------------------------------------
#

class ProcessEvent(Event):
    pass

class OnStarted(ProcessEvent):
    def __call__(self, process):
        process().on_started(self._action)
        return process

class OnStopped(ProcessEvent):
    def __call__(self, process):
        process().on_stopped(self._action)
        return process

#
# -------------------------------------------------------------------------
#   P R O C E S S  D E C O R A T O R
# -------------------------------------------------------------------------
#

class AddedStatus(grumble.Model):
    status = grumble.TextProperty()
AddedStatus.seal()

class Process(object):
    def __init__(self, *args, **kwargs):
        # TODO Grab parent process
        self.parent = kwargs.get("parent")
        self.entrypoint = kwargs.get("entrypoint")
        self.exitpoint = kwargs.get("exitpoint")
        self.start_semaphore = kwargs.get("semaphore", 1)

    def __call__(self, cls):
        logger.debug("Decorating %s as a process", cls.__name__)
        cls.add_property("starttime", grumble.DateTimeProperty())
        cls.add_property("finishtime", grumble.DateTimeProperty())
        cls.add_property("semaphore", grumble.IntegerProperty(default = 0))
        cls._statuses = {}
        for (propname, propdef) in cls.__dict__.items():
            if isinstance(propdef, Status):
                propdef.name(propname)
                cls._statuses[propname] = propdef
        cls._on_started = []
        cls._on_stopped = []
        cls._subprocesses = []
        cls._parent_process = grumble.Model.for_name(self.parent) if self.parent else None
        if cls._parent_process:
            cls._parent_process._subprocesses.append(cls)
        cls._entrypoint = self.entrypoint
        cls._exitpoint = self.exitpoint
        cls._start_semaphore = self.start_semaphore

        def get_status(cls, s):
            return cls._statuses.get(s.name() if isinstance(s, Status) else s)
        cls.get_status = classmethod(get_status)

        def statusses(cls):
            return cls._statuses
        cls.statusses = classmethod(statusses)

        def on_started(cls, action):
            cls._on_started.append(action)
        cls.on_started = classmethod(on_started)

        def on_stopped(cls, action):
            cls._on_stopped.append(action)
        cls.on_stopped = classmethod(on_stopped)

        def subprocesses(cls):
            return cls._subprocesses
        cls.subprocesses = classmethod(subprocesses)

        def instantiate(cls, parent = None):
            logger.debug("instantiate %s", cls.__name__)
            with gripe.db.Tx.begin():
                p = cls(parent = parent)
                p.put()
                for sub in cls.subprocesses():
                    subcls = grumble.Model.for_name(sub.__name__)
                    subcls.instantiate(p)
                return p
        cls.instantiate = classmethod(instantiate)

        def start(self):
            if self.starttime is None:
                with gripe.db.Tx.begin():
                    self.semaphore = self.semaphore + 1
                    if self.semaphore < self._start_semaphore:
                        logger.debug("start semaphore value is %s threshold of %s not yet reached", self.semaphore, self._start_semaphore)
                        self.put()
                        return
                    else:
                        logger.debug("starting instance of %s", self.__class__.__name__)
                        self.starttime = datetime.datetime.now()
                        self.put()
                        for a in self._on_started:
                            _queue.put_action(a, process = self)
                with gripe.db.Tx.begin():
                    ep = grumble.Model.for_name(self._entrypoint) if self._entrypoint else None
                    logger.debug("Entrypoint of %s: %s", self.__class__.__name__, ep.__name__ if ep is not None else "None")
                    if ep:
                        ep_instance = grumble.Query(ep, False, parent = self).get()
                        if ep_instance:
                            logger.debug("Starting entrypoint instance")
                            ep_instance.start()
                        else:
                            logger.debug("No entrypoint instance found")
        cls.start = start

        def stop(self):
            if self.starttime is not None and self.finishtime is None:
                logger.debug("stop instance of %s", self.__class__.__name__)
                with gripe.db.Tx.begin():
                    if self.subprocesses():
                        for sub in grumble.Query(self.subprocesses(), ancestor = self):
                            sub.stop()
                    self.finishtime = datetime.datetime.now()
                    self.put()
                    for a in self._on_stopped:
                        _queue.put_action(a, process = self)
                    if self._exitpoint:
                        p = self.parent()
                        p.stop()
        cls.stop = stop

        def has_status(self, status):
            status = status.name() if isinstance(status, Status) else status
            assert status in self._statuses, "Cannot add status %s to process %s" % (status, self.__class__.__name__)
            logger.debug("Checking status %s on process %s", status, self.__class__.__name__)
            added = None
            with gripe.db.Tx.begin():
                for s in AddedStatus.query(parent = self):
                    logger.debug(" -- Status %s found", s.status)
                    if s.status == status:
                        added = s
                return added is not None
        cls.has_status = has_status

        def add_status(self, status):
            status = status.name() if isinstance(status, Status) else status
            assert status in self._statuses, "Cannot add status %s to process %s" % (status, self.__class__.__name__)
            logger.debug("Adding status %s to process %s", status, self.__class__.__name__)
            statusdef = self._statuses[status]
            added = None
            with gripe.db.Tx.begin():
                for s in AddedStatus.query(parent = self):
                    if s.status == status:
                        added = s
                if added is None:
                    added = AddedStatus(status = status, parent = self)
                    added.put()
                    statusdef.added(self)
                return added
        cls.add_status = add_status

        def remove_status(self, status):
            status = status.name() if isinstance(status, Status) else status
            assert status in self._statuses, "Cannot remove status %s from process %s" % (status, self.__class__.__name__)
            logger.debug("Removing status %s from process %s", status, self.__class__.__name__)
            statusdef = self._statuses[status]
            remove = None
            with gripe.db.Tx.begin():
                for s in AddedStatus.query(parent = self):
                    if s.status == status:
                        remove = s
                if remove is not None:
                    grumble.delete(remove)
                    statusdef.removed(self)
                return
        cls.remove_status = remove_status

        def resolve_process(self, path):
            assert path, "Called process.resolve_process with empty path"
            logger.debug("resolving %s for %s", path, self)
            proc = self
            p = path.split("/")
            pix = 0
            maxpix = len(p)
            while pix < maxpix:
                elem = p[pix]
                pix += 1
                if elem == "..":
                    proc = proc().parent()
                    logger.debug("resolved '..' -> %s", proc)
                elif elem and elem != ".":
                    proc = grumble.Query(elem, parent = proc).get()
                    logger.debug("resolved '%s' -> %s", elem, proc)
                else:
                    logger.debug("resolve: no-op '%s'", elem)
                assert proc, "Path %s does not resolve for process %s" % (path, self)
            return proc()
        cls.resolve_process = resolve_process

        def resolve_attribute(self, path, args = None, kwargs = None):
            assert path, "Called process.resolve_attribute with empty path"
            logger.debug("resolving attribute %s for %s", path, self)
            proc = self
            (procpath, delim, attribname) = path.rpartition(":")
            call = False
            if attribname.endswith("()"):
                call = True
                attribname = attribname[:-2]
            if procpath:
                proc = self.resolve_process(procpath)()
            assert hasattr(proc, attribname), \
                "Resolving %s: Objects of class %s do not have attribute %s" % \
                (path, proc.__class__.__name__, attribname)
            attr = getattr(proc, attribname)
            if call:
                assert callable(attr), "Attribute %s of class %s is not callable" % \
                    (attribname, proc.__class__.__name__)
                if args is not None:
                    return attr(*args) if kwargs is None else attr(*args, **kwargs)
                else:
                    return attr() if kwargs is None else attr(**kwargs)
            else:
                return attr
        cls.resolve_attribute = resolve_attribute
        return cls


if __name__ == "__main__":

    @Process(entrypoint = "Step1")
    class WF(grumble.Model):
        pass

    @OnStarted(Transition("../Step2"))
    @Process(parent = "WF")
    class Step1(grumble.Model):
        pass

    @OnStarted(Invoke("./set_recipients"))
    @OnAdd("sendmail", SendMail(recipients = "@recipients",
        subject = "Grudge Test", text = "This is a test", status = "stopme"))
    @OnAdd("stopme", Stop())
    @OnStopped(Transition("../Step3"))
    @Process(parent = "WF")
    class Step2(grumble.Model):
        sendmail = Status()
        stopme = Status()
        recipients = grumble.TextProperty()

        def set_recipients(self):
            self.recipients = "runnr@de-visser.net"
            self.put()
            return self.sendmail

    @OnStarted(Add("startme"))
    @OnAdd("startme", Remove("startme"))
    @OnRemove("startme", Stop())
    @Process(parent = "WF", exitpoint = True)
    class Step3(grumble.Model):
        startme = Status()

    wf = WF.instantiate()
    wf.start()

    _queue.join()
