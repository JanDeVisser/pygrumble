/*
 * Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc., 51
 * Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 */

// if (typeof(Object.prototype.getName) !== 'function') {
//     Object.prototype.getName = function () {
//         var funcNameRegex = /function (.{1,})\(/;
//         var results = (funcNameRegex).exec((this).constructor.toString());
//         return (results && (results.length > 1)) ? results[1] : "";
//     };
// }

if (typeof(Object.create) !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o;
        return new F();
    };
}

if (typeof(String.prototype.endsWith) !== 'function') {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}
if (typeof(String.prototype.startsWith) !== 'function') {
    String.prototype.startsWith = function(prefix) {
        return this.indexOf(prefix) === 0;
    };
}
if (typeof(String.prototype.toTitleCase) !== 'function') {
    String.prototype.toTitleCase = function() {
        return this.replace(/\w\S*/g, function(txt) {
            return txt.charAt(0).toLocaleUpperCase() + txt.substr(1).toLocaleLowerCase();
        });
    };
}


if (typeof(com) !== 'object') {
    var com = {};
}

com.sweattrails = {};
com.sweattrails.api = {};
com.sweattrails.api.internal = {};
com.sweattrails.api.prototypes = {};

com.sweattrails.author = "Jan de Visser";
com.sweattrails.copyright = "(c) Jan de Visser 2012-2017 under the GPLv3 License";
com.sweattrails.api.xmlns = "http://www.sweattrails.com/html";

if (typeof(ST) !== 'object') {
    var ST = com.sweattrails.api;
    var ST_int = com.sweattrails.api.internal;
};

com.sweattrails.api.TypeError = function(t) {
  this.message = "Type error: " + t;
};

com.sweattrails.api.internal.dumpobj = function(indent, name, o) {
    if (typeof(o) === "object") {
        console.log(indent + name + ":");
        com.sweattrails.api.internal.dump(indent + "  ", o);
    } else {
        console.log(indent + name + ": " + o);
    }
};

com.sweattrails.api.internal.mydump = function(indent, o) {
    if (Array.isArray(o)) {
        console.log(indent + "[ length " + o.length);
        for (var ix  = 0; ix < o.length; ix++) {
            com.sweattrails.api.internal.dumpobj(indent + "  ", ix, o[ix]);
        }
        console.log(indent + "]");
    } else {
        for (var k in o) {
            if (o.hasOwnProperty(k)) {
                com.sweattrails.api.internal.dumpobj(indent, k, o[k]);
            }
        }
    }
};

com.sweattrails.api.dump = function(o) {
    if (arguments.length > 1) {
        console.log.apply(this, Array.prototype.slice.call(arguments, 1));
    }
    console.dir(o)
};

/* -- M A N A G E R ------------------------------------------------------ */

com.sweattrails.api.Manager = function() {
    this.id = "APIManager";
    this.type = "manager";
    this.components = [];
    this.processors = [];
    this.objects = {};
    this.deferred = [];
    this.register(this);
};

com.sweattrails.api.Manager.prototype.registerObject = function(c) {
    var t = c.type;
    var what = t
        || (c.__proto__ && c.__proto__.constructor && c.__proto__.constructor.name)
        || "unknown";
    if (!c.type) {
        c.type = what;
    }
    var name = c.id || c.name;
    if (!c.id) {
        c.id = name;
    }
    if (name) {
        (this[what] || (this[what] = {})) && (this[what][name] = c);
        t && (this[t] || (this[t] = {})) && (this[t][name] = c);
        this.objects[name] = c;
    } else {
        (this[what] || (this[what] = [])) && this[what].push(c);
        t && (this[t] || (this[t] = [])) && this[t].push(c);
    }
    return this;
};

com.sweattrails.api.Manager.prototype.register = function(c) {
    this.registerObject(c);
    this.components.push(c);
    if (c.container && c.render && this.objects.TabManager) {
        var elem = c.container;
        var renderables = this.objects.TabManager.renderables;
        for (var p = elem; p; p = p.parentNode) {
            if (p.className === "tabpage") {
                renderables = this.tab[p.id.substring(5)].renderables;
                break;
            }
        }
        renderables.push(c);
    }
    console.log("%s: registered %s, type %s (%d)", this.id, c.id, c.type, this.components.length);
    return this;
};

com.sweattrails.api.Manager.prototype.processor = function(tagname, processor) {
    this.register(processor);
    var p = { tagname: tagname, processor: processor };
    this.processors.push(p);
};

com.sweattrails.api.Manager.prototype.get = function(id) {
    return this.objects[id];
};

com.sweattrails.api.Manager.prototype.all = function(type) {
    return this[type];
};

com.sweattrails.api.Manager.prototype.onstarted = function(f) {
    this.deferred.push(f);
}

com.sweattrails.api.Manager.prototype.process = function() {
    for (var pix = 0; pix < this.processors.length; pix++) {
        var p = this.processors[pix];
        var tagname = p.tagname;
        var processor = p.processor;
        var elements = document.getElementsByTagNameNS(com.sweattrails.api.xmlns, tagname);
        this.log(this, "build(" + tagname + "): found " + elements.length + " elements");
        for ( ; elements.length > 0; ) {
            var element = elements[0];
            var parent = element.parentNode;
            processor.process(element);
            parent.removeChild(element);
        }
    }
};

com.sweattrails.api.Manager.prototype.start = function() {
    for (i in this.deferred) {
        this.deferred[i]();
    };
};

com.sweattrails.api.Manager.prototype.run = function() {
    this.dispatch("load");
    this.log(this, "Loaded");
    this.dispatch("build");
    this.log(this, "Built");
    this.process();
    this.log(this, "Processed");
    this.dispatch("start");
    this.log(this, "Started");
};

com.sweattrails.api.Manager.prototype.render = function(id) {
    this.executeOn(id, "render");
};

com.sweattrails.api.Manager.prototype.executeOn = function(id, func) {
    var obj = this.objects[id];
    obj && obj[func] && obj[func]();
};

com.sweattrails.api.Manager.prototype.dispatch = function(d) {
    for (var ix = 0; ix < this.components.length; ix++) {
        var c = this.components[ix];
        c[d] && c[d]();
    }
};

com.sweattrails.api.internal.asyncHandler = function () {
    for (var obj = $$.asyncQueue.pop(); obj; obj = $$.asyncQueue.pop()) {
        obj.onASync && obj.onASync();
    }
};

com.sweattrails.api.Manager.prototype.async = function(obj) {
    if (typeof(this.asyncQueue) === "undefined") {
        this.asyncQueue = [];
        setInterval(com.sweattrails.api.internal.asyncHandler, 0);
    }
    this.asyncQueue.push(obj);
};


com.sweattrails.api.Manager.prototype.objectlabel = function(obj) {
    var o = "";
    if (obj) {
        if (obj.type) {
            o = obj.type + ((obj.id || obj.name) && ("(" + (obj.id || obj.name) + ")"));
        } else {
            o = obj.toString();
        }
        o += ": ";
    }
    return o;
};

com.sweattrails.api.Manager.prototype.log = function(obj, msg) {
    var args = [this.objectlabel(obj) + msg];
    if (arguments.length > 2) {
        args = args.concat(Array.prototype.slice.call(arguments, 2));
    }
    console.log.apply(this, args);
};

com.sweattrails.api.Manager.prototype.assert = function(obj, condition, msg) {
    console.assert(condition, this.objectlabel(obj), msg);
};

com.sweattrails.api.Manager.prototype.dump = function() {
    com.sweattrails.api.dump.apply(this, Array.from(arguments));
};

com.sweattrails.api.STManager = new com.sweattrails.api.Manager();

function $(id) {
    return com.sweattrails.api.STManager.get(id);
}

function _$(type) {
    return com.sweattrails.api.STManager.all(type);
}

__ = com.sweattrails.api;
___ = com.sweattrails.api.internal;
$$ = __.STManager;
_ = $$.objects;

/* -- T A B -------------------------------------------------------------- */

com.sweattrails.api.BasicTab = function() {
    this.onSelect = null;
    this.onUnselect = null;
    this.onDraw = null;
    return this;
};

com.sweattrails.api.internal.Tab = function(code, label, elem) {
    this.type = "tab";
    this.impl = null;
    if (elem) {
        var factory = null;
        if (elem.getAttribute("factory")) {
            this.impl = __.getfunc(elem.getAttribute("factory"))(elem);
        } else if (elem.getAttribute("impl")) {
            this.impl = new __.getfunc(elem.getAttribute("impl"))(elem);
        } else {
            this.impl = null;
        }
        this.renderables = [];
        this.code = code;
        this.id = this.code;
        this.label = label;
        if (this.impl) {
            this.impl.initialize && this.impl.initialize(elem);
            this.impl.code = this.code;
            this.impl.label = this.label;
        }
    }
    com.sweattrails.api.STManager.register(this);
    return this;
};

com.sweattrails.api.internal.Tab.prototype.select = function() {
    if (this.impl && this.impl.onSelect) {
        this.impl.onSelect();
    }
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix];
        if (!renderable.container.hidden || (renderable.container.className === "tabpage")) {
            renderable.render();
        }
    }
    this.header.className = "tab_selected";
    this.href.className = "whitelink";
    this.page.hidden = false;
};

com.sweattrails.api.internal.Tab.prototype.unselect = function() {
    if (this.impl && this.impl.onUnselect) {
        impl.onUnselect();
    }
    this.header.className = "tab";
    this.href.className = "greylink";
    this.page.hidden = true;
};

/* -- T A B M A N A G E R ------------------------------------------------ */

com.sweattrails.api.TabManager = function() {
    if (com.sweattrails.api.tabManager) {
        alert("TabManager is a singleton!");
        return;
    }
    this.id = "TabManager";
    this.type = "manager";
    com.sweattrails.api.STManager.register(this);
    this.renderables = [];
    this.tabs = {};
    this.firsttab = null;
    this.select = function(code, ev) { this.selectTab(code); ev.stopPropagation(); };
};

com.sweattrails.api.TabManager.prototype.build = function() {
    this.pagebox = document.getElementById("pagebox");
    if (!this.pagebox) return;
    var tb = this.pagebox.getElementsByTagNameNS(com.sweattrails.api.xmlns, "tabs");
    if (tb && (tb.length > 0)) {
        var tabs_elem = tb[0];
        var tabs = getChildrenByTagNameNS(tabs_elem, com.sweattrails.api.xmlns, "tab");
        $$.log(this, "Found " + tabs.length + " tabs");
        for (var tabix = 0; tabix < tabs.length; tabix++) {
            var tab_elem = tabs[tabix];
            var tab = this.addTabFromElem(tab_elem);
            this.firsttab = this.firsttab || tab;
            tabs_elem.removeChild(tab_elem);
        }
    }
};

com.sweattrails.api.TabManager.prototype.start = function() {
    var pw = document.getElementById("page_pleasewait");
    if (pw) pw.hidden = true;
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix];
        if (renderable && renderable.render) {
            renderable.render();
        }
    }
    if (this.firsttab) {
        this.selectTab(this.firsttab.code);
    }
};

com.sweattrails.api.TabManager.prototype.addTabFromElem = function(elem) {
    var tab = this.addTab(new com.sweattrails.api.internal.Tab(elem.getAttribute("code"), elem.getAttribute("label"), elem));
    if (tab) {
        while (elem.childNodes.length > 0) {
            tab.page.appendChild(elem.childNodes[0]);
        }
    }
    return tab;
};

com.sweattrails.api.TabManager.prototype.addTab = function(tab) {
    $$.log(this, "addTab(" + tab.code + ")");
    if (!tab.impl || !tab.impl.onDraw || tab.impl.onDraw()) {
        this.drawTab(tab);
        this.tabs[tab.code] = tab;
    } else {
        $$.log(this, "Tab " + tab.code + " hidden");
        tab = null;
    }
    return tab;
};

com.sweattrails.api.TabManager.prototype.drawTab = function(tab) {
    $$.log(this, "Tab " + tab.code + " visible");
    tab.manager = this;
    var tabbox = document.getElementById("tabbox");
    var span = document.createElement("span");
    span.className = "tab";
    span.id = "tab_" + tab.code;
    span.tab = tab;
    span.onclick = this.select.bind(this, tab.code);
    tabbox.appendChild(span);
    tab.header = span;
    tab.href = document.createElement("a");
    tab.href.className = "greylink";
    tab.href.href = "#";
    tab.href.innerHTML = tab.label;
    tab.href.tab = tab;
    span.appendChild(tab.href);

    tab.page = document.getElementById("page_" + tab.code);
    if (!tab.page) {
        tab.page = document.createElement("div");
        tab.page.id = "page_" + tab.code;
        tab.page.className = "tabpage";
        tab.page.hidden = true;
        this.pagebox.appendChild(tab.page);
    }
    tab.draw && tab.draw();
};


com.sweattrails.api.TabManager.prototype.selectTab = function(code) {
    $$.log(this, "selectTab(" + code + ")");
    var newtab = this.tabs[code];
    if (newtab) {
        for (var tabcode in this.tabs) {
            var tab = this.tabs[tabcode];
            if (tab.header.className === "tab_selected") {
                if (tabcode !== code) {
                    tab.unselect();
                } else {
                    return true;
                }
            }
        }
        newtab.select();
    }
    return typeof(newtab) !== 'undefined';
};

com.sweattrails.api.tabManager = new com.sweattrails.api.TabManager();

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.DataBridge = function() {
    this.get = (arguments.length > 0) ? arguments[0] : null;
    this.set = (arguments.length > 1) ? arguments[1] : null;
};

Object.defineProperty(com.sweattrails.api.internal.DataBridge.prototype, "get", {
    get: function() {
        return this._getvalue;
    },
    set: function(getvalue) {
        this._getvalue = getvalue;
        this._getstatic = null;
        this._getter = null;
        this._getprop = null;
        if (getvalue) {
            if (typeof(getvalue) === "string") {
                if (getvalue.startsWith("=")) {
                    this._getstatic = getvalue.substring(1);
                } else if (getvalue.endsWith("()")) {
                    this._getter = __.getfunc(g.substring(0, g.length() - 2), null, this);
                } else {
                    this._getprop = getvalue;
                }
            } else if (typeof(g) === "function") {
                this._getter = g.bind(this);
            } else {
                this._getstatic = getvalue;
            }
        }
    }
});

Object.defineProperty(com.sweattrails.api.internal.DataBridge.prototype, "set", {
    get: function() {
        return this._setvalue;
    },
    set: function(setvalue) {
        this._setvalue = setvalue;
        this._setter = null;
        this._setprop = null;
        var s = this._setvalue || this.get;
        if (s) {
            if ((typeof(s) === "string") && s.endsWith("()")) {
                this._setter = __.getfunc(s.substring(0, s.length() - 2), null, this);
            } else if (typeof(s) === "function") {
                this._setter = s.bind(this);
            } else {
                this._setprop = s.toString();
            }
        }
    }
});

com.sweattrails.api.internal.DataBridge.prototype.setValue = function(object, value) {
    try {
        if (this._setter) {
        	this._setter(object, value);
        } else if (this._setprop) {
            __.setvar(this._setprop, value, object);
        }
    } catch (e) {
        console.trace("Exception in Databridge.setValue: " + e);
        com.sweattrails.api.dump(object, "bridge.set: " + this.set + " object =");
        throw e;
    }
};

com.sweattrails.api.internal.DataBridge.prototype.getValue = function(object) {
    try {
        var context = (arguments.length > 1) ? arguments[1] : window;
        if (this._getstatic) {
            return this._getstatic;
        } else if (this._getter) {
            return this._getter(object, context);
        } else if (this._get !== null) {
            return __.getvar(this._get, object);
        } else {
            return null;
        }
    } catch (e) {
        console.trace("Exception in Databridge.getValue: " + e);
        com.sweattrails.api.dump(object, "bridge.get: " + this.get + " object =");
        throw e;
    }
};

com.sweattrails.api.internal.DataBridge.prototype.clear = function(object) {
    if (this._setter) {
    	this._setter(object, null);
    } else if (this._set) {
        __.clearvar(this._set, object);
    }
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.walkname = function (name, ns) {
    ns = ns || window;
    name = name || "";
    var components = name.split(".");
    var component = null;
    for (var ix = 0; ix < (components.length - 1); ix++) {
        component = components[ix].trim();
        if (!(component in ns)) {
            ns[component] = {};
        }
        ns = ns[component];
    }
    component = components[ix].trim();
    return [ ns, component ];
};

com.sweattrails.api.getvar = function (name, ns) {
    ns = ns || window;
    name = name || "";
    var components = name.split(".");
    for (var ix = 0; ns && (ix < components.length); ix++) {
        var component = components[ix].trim();
        if (component in ns) {
            ns = ns[component];
        } else {
            ns = null;
        }
    }
    return ns;
};

getvar = __.getvar;

com.sweattrails.api.clearvar = function (name, ns) {
    var wn = ___.walkname(name, ns);
    if (wn[0] && wn[1]) {
        wn[0][wn[1]] = null;
    }
    return ns;
};

com.sweattrails.api.setvar = function (name, value, ns) {
    var wn = ___.walkname(name, ns);
    if (wn[0] && wn[1]) {
        ns = wn[0];
        var component = wn[1];
        if ((typeof(ns[component]) !== 'undefined') && ns[component]) {
            if (Array.isArray(ns[component])) {
                ns[component].push(value);
            } else {
                ns[component] = [ns[component], value];
            }
        } else {
            ns[component] = value;
        }
    }
    return ns;
};

setvar = __.setvar;

com.sweattrails.api.getfunc = function (func, ns, thisObj) {
    var f = null;
    if (typeof(func) === "function") {
        f = func;
    } else {
        ns = (arguments.length > 1) ? ns : null;
        var v = __.getvar(func, ns);
        f = (typeof(v) === "function") && v;
    }
    if (f && thisObj) {
        f = f.bind(thisObj);
    }
    return f;
};

getfunc = __.getfunc;

/**
 * Builder - Abstract base class for element builders.
 */

com.sweattrails.api.BuilderFlags = {};
com.sweattrails.api.BuilderFlags.Int = 1;
com.sweattrails.api.BuilderFlags.Float = 2;
com.sweattrails.api.BuilderFlags.Function = 4;
com.sweattrails.api.BuilderFlags.Boolean = 8;

com.sweattrails.api.Builder = function(tagname, objclass) {
    if (tagname) {
        this.type = "builder";
        this.name = tagname + "builder";
        this.objclass = objclass;
        $$.processor(tagname, this);
    }
}

com.sweattrails.api.Builder.prototype.process = function(elem) {
    var name = elem.getAttribute("name");
    $$.log(this, "Building %s", name);
    var obj = new this.objclass(elem.parentNode, name);
    com.sweattrails.api.GritObject.mixin(obj);
    obj.build(elem);
    if (obj.hasDataSource) {
        obj.buildDataSource(elem);
    }
};


/**
 * GritObject mix-in.
 */

com.sweattrails.api.GritObject = {};

com.sweattrails.api.GritObject.set = function (elem, tag, property, flags) {
    property = property || tag;
    var val = elem.getAttribute(tag);
    var converted = null;
    flags = flags || 0;
    if (val) {
        if (flags | com.sweattrails.api.BuilderFlags.Int) {
            converted = parseInt(val);
        }
        if (!converted && (flags | com.sweattrails.api.BuilderFlags.Float)) {
            converted = parseFloat(val);
        }
        if (!converted && (flags | com.sweattrails.api.BuilderFlags.Function) && (val.endsWith("()"))) {
            converted = __.getfunc(val.substring(0, val.length - 2));
        }
        if (!converted && (flags | com.sweattrails.api.BuilderFlags.Boolean)) {
            converted = val === "true";
        }
    }
    if (!converted) {
        converted = val;
    }
    if (typeof(property) === "function") {
        property.call(this, converted);
    } else if (val) {
        __.clearvar(property, this);
        __.setvar(property, converted, this);
    }
    return this;
};

com.sweattrails.api.GritObject.buildChildren = function (elem, tag, childcls) {
    var elems = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, tag);
    for (var j = 0; j < elems.length; j++) {
        var child = new childcls(this);
        com.sweattrails.api.GritObject.mixin(child);
        child.build(elems[j]);
    }
    return this;
}

com.sweattrails.api.GritObject.setDataSource = function (ds) {
    if (ds) {
        this.datasource = ds;
        ds.addView(this);
    }
};

com.sweattrails.api.GritObject.buildDataSource = function (elem) {
    if (_.DataSourceBuilder) {
        this.setDataSource(_.DataSourceBuilder.build(elem));
    }
};

com.sweattrails.api.GritObject.mixin = function (obj) {
    obj.set = com.sweattrails.api.GritObject.set.bind(obj);
    obj.buildChildren = com.sweattrails.api.GritObject.buildChildren.bind(obj);
    if (obj.hasDataSource) {
        obj.setDataSource = com.sweattrails.api.GritObject.setDataSource.bind(obj);
        obj.buildDataSource = com.sweattrails.api.GritObject.buildDataSource.bind(obj);
    }
};

/* ----------------------------------------------------------------------- */

function getChildrenByTagNameNS(elem, ns, tagname) {
    var ret = [];
    var nodes = elem.childNodes;
    for (var ix = 0; ix < nodes.length; ix++) {
        var c = nodes[ix];
        if ((c.namespaceURI === ns) && (c.localName === tagname)) {
            ret.push(c);
        }
    }
    return ret;
};

function hasChildWithTagNameNS(elem, ns, tagname) {
    var nodes = elem.childNodes;
    for (var ix = 0; ix < nodes.length; ix++) {
        var c = nodes[ix];
        if ((c.namespaceURI === ns) && (c.localName === tagname)) {
            return true;
        }
    }
    return false;
};

com.sweattrails.api.renderObject = function(elem, content) {
    if ((typeof(content) === "object") && (typeof(content["render"]) === "function")) {
        content = content.render();
    }
    if (typeof(content) === "string") {
        elem.innerHTML = content;
    } else if (!content) {
        elem.innerHTML = "&#160;";
    } else {
        $$.log($$, "elem: " + elem + ", typeof: " + typeof(elem) + " rendering " + content + ", type " + typeof(content));
        elem.appendChild(content);
    }
};


com.sweattrails.api.internal.DOMElementLike = function(obj, ns, tagname) {
    this._ns = ns;
    this._tagname = tagname;
    this.object = obj || {};
};

com.sweattrails.api.internal.DOMElementLike.prototype.getAttribute = function(attr) {
    if (typeof(this.object) !== "object") {
        return null;
    } else {
        ret = (attr in this.object) ? this.object[attr] : null;
        if (["number", "string", "boolean"].indexOf(typeof(ret)) >= 0) {
            ret = ret.toString();
        } else {
            ret = null;
        }
        return ret;
    }
};

Object.defineProperty(com.sweattrails.api.internal.DOMElementLike.prototype, "childNodes", {
    get: function() {
        var ret = [];
        var ns = this._ns;
        if (typeof(this.object) === "object") {
            for (var c in this.object) {
                if (!this.object.hasOwnProperty(c)) continue;
                var o = this.object[c];
                o = (Array.isArray(o)) ? o : [o];
                o.forEach(function(child) {
                    var node = new com.sweattrails.api.internal.DOMElementLike(child, ns, c);
                    ret.append(node);
                });
            }
        } else {
            ret.append(this.object.toString());
        }
        return ret;
    }
});

Object.defineProperty(com.sweattrails.api.internal.DOMElementLike.prototype, "nodeValue", {
    get: function() {
        var ret = null;
        if (typeof(this.object) !== "object") {
            ret = this.object.toString();
        }
        return ret;
    }
});

Object.defineProperty(com.sweattrails.api.internal.DOMElementLike.prototype, "namespaceURI", {
    get: function() {
        return this._ns;
    }
});

Object.defineProperty(com.sweattrails.api.internal.DOMElementLike.prototype, "localName", {
    get: function() {
        return this._tagname;
    }
});

getDOMElement = function(obj) {
    return (obj && obj.getAttribute) ? obj : new com.sweattrails.api.internal.DOMElementLike(obj, ST.xmlns, "object");
};

/*
 * MAYBE MOVE ME
 */

function login_error(errorinfo) {
    if (errorinfo !== 401) return false;
    this.$["password"].clear();
    this.header.error("Mistyped email or password");
    this.footer.error();
    return true;
}

function signup_submitted() {
    st_alert("Your signup request is being processed. Check your email for further instructions.");
}

function password_changed() {
    st_alert("Your password is changed. Remember to use your new password the next time you check in.");
}

/*
 * MOVE ME MOVE ME
 */

function rpad(num, width) {
    var n = num + "";
    while (n.length < 2) n = "0" + n;
    return n;
}

function obj_to_datetime(obj) {
    if (obj) {
        return new Date(
                ((typeof(obj.year) !== "undefined") && obj.year) || 1970,
                ((typeof(obj.month) !== "undefined") && (obj.month - 1)) || 0,
                ((typeof(obj.day) !== "undefined") && obj.day) || 0,
                ((typeof(obj.hour) !== "undefined") && obj.hour) || 0,
                ((typeof(obj.minute) !== "undefined") && obj.minute) || 0,
                ((typeof(obj.second) !== "undefined") && obj.minute) || 0);
    } else {
        return null;
    }
}

function date_to_obj(d) {
    d = d || new Date();
    return {
        'year': d.getUTCFullYear(),
        'month': d.getUTCMonth() + 1,
        'day': d.getUTCDate()
    };
}

function time_to_obj(d) {
    d = d || new Date();
    var ret = {
        'hour': d.getUTCHours(),
        'minute': d.getUTCMinutes(),
        'second': d.getUTCSeconds()
    };
    // $$.log($$, "time_to_obj -> " + ret.hour + ":" + ret.minute + ":" + ret.second)
    return ret
}

function datetime_to_obj(d) {
    d = d || new Date();
    var ret = {
        'year': d.getUTCFullYear(),
        'month': d.getUTCMonth() + 1,
        'day': d.getUTCDate(),
        'hour': d.getUTCHours(),
        'minute': d.getUTCMinutes(),
        'second': d.getUTCSeconds()
    };
    // $$.log($$, "datetime_to_obj: " + format_datetime(ret));
    return ret;
}

function seconds_to_timeobj(secs) {
    // $$.log($$, "Converting " + secs + " seconds to time object")
    return time_to_obj(new Date(secs * 1000));
}
seconds_to_time = seconds_to_timeobj

function timeobj_to_seconds(t) {
    return (t) ? t.hour * 3600 + t.minute * 60 + t.second : 0;
}

function time_after_offset(t, offset) {
    return seconds_to_time(timeobj_to_seconds(t) - offset);
}

function format_date(d) {
    if (d && (d.year > 0) && (d.month > 0) && (d.day > 0)) {
        return (true /* metric() */)
            ? rpad(d.day, 2) + "-" + rpad(d.month, 2) + "-" + d.year
            : rpad(d.month, 2) + "/" + rpad(d.day, 2) + "/" + d.year;
    } else {
        return null;
    }
}

function format_time(d) {
    if (false /* imperial() */) {
        var ampm = ((d.hour < 12) && "am") || "pm";
        return rpad(((d.hour < 13) && d.hour) || (d.hour - 12), 2)  + ":" + rpad(d.minute, 2) + ampm;
    } else {
        return rpad(d.hour, 2)  + ":" + rpad(d.minute, 2);
    }
}

function format_elapsed_time(t) {
    var s = "";
    if (t.hour > 0) {
        s = rpad(t.hour, 2) + ":";
    }
    s += rpad(t.minute, 2) + ":" + rpad(t.second, 2);
    return s;
}

function format_datetime(value, format) {
   return format_date(value) + " " + format_time(value);
}

function prettytime(value) {
    if (!value) value = new Date(0);
    var ret = "";
    if (value.hour > 0) {
	    ret = value.hour + "hr ";
    }
    if (value.minute > 0) {
	    ret += value.minute + "min ";
    }
    ret += value.second + "s";
    return ret;
}

function import_file(url, callback) {
    // Brute-force XSS denial:
    if ((url.indexOf("http://") === 0) || (url.indexOf("https://") === 0)) {
        return;
    }
    var head = document.getElementsByTagName('head')[0];
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = url;

    if (typeof(callback) === "function") {
        script.onreadystatechange = callback;
        script.onload = callback;
    }
    head.appendChild(script);
}


// ------------------------------------------------------------------------
