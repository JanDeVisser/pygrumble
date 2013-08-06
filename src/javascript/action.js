/**
 * FormAction -
 */

com.sweattrails.api.internal.EditAction = function() { this.id = "edit" }

com.sweattrails.api.internal.EditAction.prototype.onClick = function() {
    this.action.owner.render("edit")
}

com.sweattrails.api.internal.NewAction = function() { this.id = "new" }

com.sweattrails.api.internal.NewAction.prototype.onClick = function() {
    (this.action.owner.openForm && this.action.owner.openForm(null)) || this.action.owner.render("new")
}

com.sweattrails.api.internal.SaveAction = function(elem) {
    if (elem.getAttribute("onsubmitted")) {
        this.onsubmitted = getfunc(elem.getAttribute("onsubmitted"));
    }
    if (elem.getAttribute("redirect")) {
        var destination = elem.getAttribute("redirect");
        console.log("SaveAction.redirect: " + destination);
        this.onredirect = function(href) { return destination; };
    }
    this.id = "save";
}

com.sweattrails.api.internal.SaveAction.prototype.onClick = function() {
    if (this.onsubmitted) {
        this.action.owner.onsubmitted = this.onsubmitted.bind(this.action.owner);
    }
	this.action.container.inprogress = this;
    this.action.owner.submit();
}

com.sweattrails.api.internal.CancelAction = function() { this.id = "cancel" }

com.sweattrails.api.internal.CancelAction.prototype.onClick = function() {
    this.action.owner.close()
}

com.sweattrails.api.internal.HTMLAction = function(elem) {
    this.id = "html"
    this.nodes = []
    for (var nix = 0; nix < elem.childNodes.length; nix++) {
        this.nodes.push(elem.childNodes[nix])
    }
}

com.sweattrails.api.internal.HTMLAction.prototype.render = function(parent) {
    for (var nix = 0; nix < this.nodes.length; nix++) {
        parent.appendChild(this.nodes[nix])
    }
}

com.sweattrails.api.internal.CustomAction = function(name, action) {
    this.name = name || action
    this.onclick = getfunc(action)
    this.id = "custom"
}

com.sweattrails.api.internal.CustomAction.prototype.onClick = function() {
    this.onclick(this.action.owner, this.action)
}

com.sweattrails.api.internal.actions = {}
com.sweattrails.api.internal.actions.edit = com.sweattrails.api.internal.EditAction
com.sweattrails.api.internal.actions.new = com.sweattrails.api.internal.NewAction
com.sweattrails.api.internal.actions.save = com.sweattrails.api.internal.SaveAction
com.sweattrails.api.internal.actions.cancel = com.sweattrails.api.internal.CancelAction
com.sweattrails.api.internal.actions.html = com.sweattrails.api.internal.HTMLAction

com.sweattrails.api.ActionContainer = function(owner) {
    this.id = ((arguments.length > 1) && arguments[1]) || "actions"
    this.owner = owner
    this.type = "actions"
    this.location = ((arguments.length > 1) && arguments[1]) || "header"
    $$.register(this)
    this.actions = []
    return this
}

Object.defineProperty(com.sweattrails.api.ActionContainer.prototype, "id", {
    get: function() { return this.owner.id + "-" + this._id },
    set: function(id) {
        this._id = id
    }
})

com.sweattrails.api.ActionContainer.prototype.add = function(action) {
    this.actions.push(action)
    action.owner = this.owner
}

com.sweattrails.api.ActionContainer.prototype.build = function(elem) {
    if (!elem) return // FIXME -- when we register as a component this gets called.
    elem = getDOMElement(elem)
    var actions = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "action")
    for (var i = 0; i < actions.length; i++) {
        this.buildAction(actions[i])
    }
}

com.sweattrails.api.ActionContainer.prototype.buildAction = function(a) {
    a = getDOMElement(a)
    var action = new com.sweattrails.api.Action(a.getAttribute("name"), a.getAttribute("action"))
    action.build(a)
    action.container = this
    this.add(action)
    return action
}


com.sweattrails.api.ActionContainer.prototype.erase = function() {
    if (this.actionbar) {
    	this.owner.container.removeChild(this.actionbar)
    	this.actionbar = null
    }
}

com.sweattrails.api.ActionContainer.prototype.getActiveActions = function() {
    var a = []
    var aix = 0
    var action = null
    for (aix = 0; aix < this.actions.length; aix++) {
        action = this.actions[aix]
        if (action.isActive()) a.push(action)
    }
    return a
}

com.sweattrails.api.ActionContainer.prototype.render = function() {
    a = this.getActiveActions()

    this.actionbar = document.createElement("div")
    this.actionsdiv = document.createElement("div")
    if (a.length > 0) {
    	this.actionsdiv.className = "buttonbar-" + this.location
    } else {
    	this.actionsdiv.className = "buttonbar-empty"
    }
    this.actionsdiv.id = this.id + "-actionbar"
    this.actionbar.appendChild(this.actionsdiv)
    this.progressbar = document.createElement("div")
    this.progressbar.className = "buttonbar-" + this.location
    this.progressbar.id = this.id + "-progressbar"
    this.progressbar.hidden = true
    this.throbber = document.createElement("img")
    this.throbber.id = this.progressbar.id + "-throbber"
    this.throbber.src = "/image/throbber.gif"
    this.throbber.height = this.throbber.width = 32
    this.progressbar.appendChild(this.throbber)
    this.progressmsg = document.createElement("span")
    this.progressmsg.id = this.progressbar.id + "-message"
    this.progressbar.appendChild(this.progressmsg)
    this.actionbar.appendChild(this.progressbar)
    this.owner.container.appendChild(this.actionbar)

    for (var aix = 0; aix < a.length; aix++) {
        if (aix > 0) {
            var span = document.createElement("span")
            span.innerHTML = " | "
            this.actionsdiv.appendChild(span)
        }
        a[aix].render(this.actionsdiv)
    }
}

com.sweattrails.api.ActionContainer.prototype.progressOff = function() {
    this.actionsdiv.hidden = false
    this.progressbar.hidden = true
    this.progressbar.className = "progressmessage"
    this.throbber.src = "/image/throbber.gif"
    this.progressmsg.innerHTML = ""
    return true
}


com.sweattrails.api.ActionContainer.prototype.progress = function(msg) {
    if (msg) {
        this.actionsdiv.hidden = true
        this.progressbar.hidden = false
        this.progressbar.className = "progressmessage"
        this.throbber.src = "/image/throbber.gif"
        this.progressmsg.innerHTML = msg
    } else {
        this.progressOff()
    }
    return true
}

com.sweattrails.api.ActionContainer.prototype.error = function(msg) {
    if (msg) {
        this.actionsdiv.hidden = true
        this.progressbar.hidden = false
        this.progressbar.className = "errormessage"
        this.throbber.src = "/image/error.png"
        this.progressmsg.innerHTML = msg
    } else {
        this.progressOff()
    }
    return true
}

com.sweattrails.api.ActionContainer.prototype.onDataSubmitted = function() {
    this.inprogress && this.inprogress.onDataSubmitted && this.inprogress.onDataSubmitted()
    this.inprogress = null
}

com.sweattrails.api.ActionContainer.prototype.onDataError = function(errorinfo) {
    this.inprogress && this.inprogress.onDataError && this.inprogress.onDataError(errorinfo)
    this.inprogress = null
}

com.sweattrails.api.ActionContainer.prototype.onDataEnd = function() {
    this.inprogress && this.inprogress.onDataEnd && this.inprogress.onDataEnd()
    this.inprogress = null
}

// --------------------------------------------------------------------------
// --------------------------------------------------------------------------

com.sweattrails.api.Action = function(id, action) {
    this.type = "action"
    this.name = this.id = (id || action)
}

com.sweattrails.api.Action.prototype.build = function(a) {
    a = getDOMElement(a)
    var ac = a.getAttribute("action")
    this.label = a.getAttribute("label")
    this.modes = a.getAttribute("mode")
    var impl = null
    if (ac) {
    	var factory = com.sweattrails.api.internal.actions[ac]
        if (factory) {
            this.impl = new factory(a)
        } else {
            this.impl = new com.sweattrails.api.internal.CustomAction(a.getAttribute("name"), a.getAttribute("action"))
        }
    }
    this.action = (this.impl && this.impl.id) || "unknown"
    if (this.impl) this.impl.action = this
    $$.register(this)
    if (a.getAttribute("isactive")) {
        this.isactive = getfunc(a.getAttribute("isactive"))
    }
    if (a.getAttribute("ondone")) {
        this.onDataEnd = getfunc(a.getAttribute("ondone"))
    }
    if (a.getAttribute("redirect")) {
        this.onDataEnd = this.doRedirect.bind(this, a.getAttribute("redirect"))
    }
}

com.sweattrails.api.Action.prototype.isActive = function() {
    if (this.modes && this.owner.mode && (this.modes.indexOf(this.owner.mode) < 0)) {
        return false
    } else {
        return this.isactive ? this.isactive() : true
    }
}

com.sweattrails.api.Action.prototype.doRedirect = function(redirect) {
    console.log("Action::doRedirect: " + redirect)
    document.location = redirect
}

com.sweattrails.api.Action.prototype.render = function(parent) {
    var ret = null
    if (!this.impl || !this.impl.render) {
        ret = document.createElement("a")
        ret.className = "menulink"
        ret.href = "#"
        ret.innerHTML = this.label || this.name || this.action
        ret.id = this.owner.id + "-" + (this.name || this.action) + "-action"
        ret.action = this
        ret.onclick = function(e) { e.currentTarget.action.onClick(); return true; }
        parent.appendChild(ret)
    } else {
        ret = this.impl.render(parent)
    }
    return ret
}

com.sweattrails.api.Action.prototype.onClick = function() {
    if ((this.owner.inprogress == null) && this.impl) {
        this.impl.onClick()
    }
}

