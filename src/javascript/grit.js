if (typeof(com) !== 'object') {
    var com = {}
}
com.sweattrails = {}
com.sweattrails.api = {}
com.sweattrails.api.internal = {}
com.sweattrails.api.prototypes = {}

com.sweattrails.author = "Jan de Visser"
com.sweattrails.copyright = "(c) Jan de Visser 2012 under the BSD License"
com.sweattrails.api.xmlns = "http://www.sweattrails.com/html"

if (typeof(ST) !== 'object') {
    var ST = com.sweattrails.api
}

if (typeof(Object.create) !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o
        return new F()
    }
}

com.sweattrails.api.Manager = function() {
    this.id = "APIManager"
    this.type = "manager"
    this.components = []
    this.processors = []
    this.objects = {}
    this.register(this)
}

com.sweattrails.api.Manager.prototype.register = function(c) {
    var t = c.type
    var what = t
            || (c.__proto__ && c.__proto__.constructor && c.__proto__.constructor.name)
            || "unknown"
    var name = c.id || c.name
    if (name) {
        (this[what] || (this[what] = {})) && (this[what][name] = c)
        t && (this[t] || (this[t] = {})) && (this[t][name] = c)
        this.objects[name] = c
    } else {
        (this[what] || (this[what] = [])) && this[what].push(c)
        t && (this[t] || (this[t] = [])) && this[t].push(c)
    }
    this.components.push(c)
    if (c.container && c.render && this.objects.TabManager) {
        var elem = c.container
        var renderables = this.objects.TabManager.renderables
        for (var p = elem; p != null; p = p.parentNode) {
            if (p.className == "tabpage") {
                renderables = this.tab[p.id.substring(5)].renderables
                break
            }
        }
        renderables.push(c)
    }
    console.log(this.id + ": registered: " + name + ", type " + t + " (" + this.components.length + ")")
}

com.sweattrails.api.Manager.prototype.processor = function(tagname, processor) {
    this.register(processor)
    var p = { tagname: tagname, processor: processor }
    this.processors.push(p)
}

com.sweattrails.api.Manager.prototype.get = function(id) {
    return this.objects[id]
}

com.sweattrails.api.Manager.prototype.all = function(type) {
    return this[type]
}

com.sweattrails.api.Manager.prototype.process = function() {
    for (var pix = 0; pix < this.processors.length; pix++) {
        var p = this.processors[pix]
        var tagname = p.tagname
        var processor = p.processor
        var elements = document.getElementsByTagNameNS(com.sweattrails.api.xmlns, tagname)
        this.log(this, "build(" + tagname + "): found " + elements.length + " elements")
        for ( ; elements.length > 0; ) {
            var element = elements[0]
            var parent = element.parentNode
            processor.process(element)
            parent.removeChild(element)
        }
    }
}

com.sweattrails.api.Manager.prototype.run = function() {
    this.dispatch("load")
    this.dispatch("build")
    this.process()
    this.dispatch("start")
}

com.sweattrails.api.Manager.prototype.render = function(id) {
    this.executeOn(id, "render")
}

com.sweattrails.api.Manager.prototype.executeOn = function(id, func) {
    var obj = this.objects[id]
    obj && obj[func] && obj[func]()
}

com.sweattrails.api.Manager.prototype.dispatch = function(d) {
    for (var ix = 0; ix < this.components.length; ix++) {
        var c = this.components[ix]
        c[d] && c[d]()
    }
}

com.sweattrails.api.Manager.prototype.log = function(obj, msg) {
    var o = obj.type + ((obj.id || obj.name) && ("(" + (obj.id||obj.name) + ")"))
    console.log(o + ": " + msg)
}

com.sweattrails.api.STManager = new com.sweattrails.api.Manager()

function $(id) {
    return com.sweattrails.api.STManager.get(id)
}

function _$(type) {
    return com.sweattrails.api.STManager.all(type)
}

$$ = com.sweattrails.api.STManager
_ = $$.objects

com.sweattrails.api.BasicTab = function() {
    this.onSelect = null
    this.onUnselect = null
    this.onDraw = null
    return this
}

com.sweattrails.api.internal.Tab = function(code, label, elem) {
    this.type = "tab"
    this.impl = null
    if (elem) {
        var factory = null
        if (elem.getAttribute("factory")) {
            factory = new Function("tab", "return " + elem.getAttribute("factory") + "(tab)")
        } else if (elem.getAttribute("impl")) {
            factory = new Function("return new " + elem.getAttribute("impl") + "()")
        }
        this.impl = factory && factory(elem)
        this.renderables = []
        this.code = code
        this.id = this.code
        this.label = label
        if (this.impl) {
            this.impl.initialize && this.impl.initialize(elem)
            this.impl.code = this.code
            this.impl.label = this.label
        }
    }
    com.sweattrails.api.STManager.register(this)
    return this
}

com.sweattrails.api.internal.Tab.prototype.select = function() {
    if (this.impl && this.impl.onSelect) {
        this.impl.onSelect()
    }
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix]
        if (!renderable.container.hidden || (renderable.container.className == "tabpage")) {
            renderable.render()
        }
    }
    this.header.className = "tab_selected"
    this.page.hidden = false
}

com.sweattrails.api.internal.Tab.prototype.unselect = function() {
    if (this.impl && this.impl.onUnselect) {
        impl.onUnselect()
    }
    this.header.className = "tab"
    this.page.hidden = true
}

com.sweattrails.api.TabManager = function() {
    if (com.sweattrails.api.tabManager != null) {
	alert("TabManager is a singleton!")
	return null
    }
    this.id = "TabManager"
    this.type = "manager"
    com.sweattrails.api.STManager.register(this)
    this.renderables = []
    this.tabs = {}
    this.firsttab = null
    this.select = function(code, ev) { this.selectTab(code); ev.stopPropagation() }
    return this
}

com.sweattrails.api.TabManager.prototype.build = function() {
    this.pagebox = document.getElementById("pagebox")
    $$.log(this, "Pagebox is " + ((this.pagebox) ? "NOT " : "") + "null")
    var tb = document.getElementsByTagNameNS(com.sweattrails.api.xmlns, "tabs")
    if (tb && (tb.length > 0)) {
        tabs_elem = tb[0]
        $$.log(this, "Found tabs element")
        var tabs = getChildrenByTagNameNS(tabs_elem, com.sweattrails.api.xmlns, "tab")
        $$.log(this, "Found " + tabs.length + " tabs")
        for (var tabix = 0; tabix < tabs.length; tabix++) {
            var tab_elem = tabs[tabix]
            var tab = this.addTabFromElem(tab_elem)
            this.firsttab = this.firsttab || tab
            tabs_elem.removeChild(tab_elem)
        }
    } else {
        $$.log(this, "*** TABS ELEMENT NOT FOUND ***")
    }
}

com.sweattrails.api.TabManager.prototype.start = function() {
    var pw = document.getElementById("page_pleasewait")
    pw.hidden = true
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix]
        if (renderable && renderable.render) {
            renderable.render()
        }
    }
    if (this.firsttab != null) {
        this.selectTab(this.firsttab.code)
    }
}

com.sweattrails.api.TabManager.prototype.addTabFromElem = function(elem) {
    tab = this.addTab(new com.sweattrails.api.internal.Tab(elem.getAttribute("code"), elem.getAttribute("label"), elem))
    if (tab) {
        while (elem.childNodes.length > 0) {
            tab.page.appendChild(elem.childNodes[0])
        }
    }
    return tab
}

com.sweattrails.api.TabManager.prototype.addTab = function(tab) {
    $$.log(this, "addTab(" + tab.code + ")")
    if ((tab.impl == null) || (tab.impl.onDraw == null) || tab.impl.onDraw()) {
        this.drawTab(tab)
        this.tabs[tab.code] = tab
    } else {
        $$.log(this, "Tab " + tab.code + " hidden")
        tab = null
    }
    return tab
}

com.sweattrails.api.TabManager.prototype.drawTab = function(tab) {
    $$.log(this, "Tab " + tab.code + " visible")
    var onclick = this.select.bind(this, tab.code)
    tab.manager = this
    var tabbox = document.getElementById("tabbox")
    var span = document.createElement("span")
    span.className = "tab"
    span.id = "tab_" + tab.code
    span.tab = tab
    span.onclick = onclick
    tabbox.appendChild(span)
    tab.header = span
    var href = document.createElement("a")
    href.href = "#"
    href.innerHTML = tab.label
    href.tab = tab
    href.onclick = onclick
    span.appendChild(href)

    tab.page = document.getElementById("page_" + tab.code)
    if (tab.page == null) {
        tab.page = document.createElement("div")
        tab.page.id = "page_" + tab.code
        tab.page.className = "tabpage"
        tab.page.hidden = true
        this.pagebox.appendChild(tab.page)
    }
}


com.sweattrails.api.TabManager.prototype.selectTab = function(code) {
    //$$.log(this, "selectTab(" + code + ")")
    for (var tabcode in this.tabs) {
        var tab = this.tabs[tabcode]
        if (code == tab.code) {
            if (tab.header.className != "tab_selected") {
                tab.select()
            }
        } else if (tab.header.className == "tab_selected") {
            tab.unselect()
        }
    }
    return true
}

com.sweattrails.api.tabManager = new com.sweattrails.api.TabManager()

com.sweattrails.api.internal.DataBridge = function() {
    this.get = null
    this.set = null
}

com.sweattrails.api.internal.DataBridge.prototype.setValue = function(object, value) {
    var s = this.set || this.get
    if (typeof(s) == "function") {
	s(object, value)
    } else if (s) {
        var p = s
        var o = object
        for (var dotix = p.indexOf("."); (dotix > 0) && (dotix < (p.length-1)); dotix = p.indexOf(".")) {
            var subp = p.substring(0, dotix)
            if (o) {
                if (!o[subp]) o[subp] = {}
                o = o[subp]
            }
            p = p.substring(dotix + 1)
        }
	if (o) o[p] = value
    }
}


com.sweattrails.api.internal.DataBridge.prototype.getValue = function(object, context) {
    var ret = null
    if (typeof(this.get) == "function") {
	ret = this.get(object, context)
    } else if (this.get != null) {
        var p = this.get
        var o = object
        for (var dotix = p.indexOf("."); (dotix > 0) && (dotix < (p.length-1)); dotix = p.indexOf(".")) {
            o = o && o[p.substring(0, dotix)]
            p = p.substring(dotix + 1)
        }
	ret = o && o[p]
    }
    return ret
}


function getfunc(fname) {
    return ((typeof(this[fname]) == "function") && this[fname]) ||
           ((typeof(com.sweattrails.api[fname]) == "function") && com.sweattrails.api[fname])
}

function getChildrenByTagNameNS(elem, ns, tagname) {
    var ret = []
    for (var ix = 0; ix < elem.childNodes.length; ix++) {
        var c = elem.childNodes[ix]
        if ((c.namespaceURI == ns) && (c.localName == tagname)) ret.push(c)
    }
    return ret
}

com.sweattrails.api.renderObject = function(elem, content) {
    if ((typeof(content) == "object") && (typeof(content.render) == "function")) {
        content = content.render()
    }
    if (typeof(content) == "string") {
        elem.innerHTML = content
    } else if (content == null) {
        elem.innerHTML = "&#160;"
    } else {
        elem.appendChild(content)
    }
}

