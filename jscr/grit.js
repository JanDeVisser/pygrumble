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
//     }
// }

if (typeof(Object.create) !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o;
        return new F();
    }
}

if (typeof(String.prototype.endsWith) !== 'function') {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    }
}
if (typeof(String.prototype.startsWith) !== 'function') {
    String.prototype.startsWith = function(prefix) {
        return this.indexOf(prefix) === 0;
    }
}
if (typeof(String.prototype.toTitleCase) !== 'function') {
    String.prototype.toTitleCase = function() {
        return this.replace(/\w\S*/g, function(txt) {
            return txt.charAt(0).toLocaleUpperCase() + txt.substr(1).toLocaleLowerCase();
        });
    }
}

const has = Object.prototype.hasOwnProperty;

if (typeof(com) !== 'object') {
    var com = {}
}

com.sweattrails = {}
com.sweattrails.api = {}
com.sweattrails.api.internal = {}
com.sweattrails.api.prototypes = {}

com.sweattrails.author = "Jan de Visser";
com.sweattrails.copyright = "(c) Jan de Visser 2012-2018 under the GPLv3 License";
com.sweattrails.api.xmlns = "http://www.sweattrails.com/html";

var ST = com.sweattrails.api;
var ST_int = com.sweattrails.api.internal;
var __ = com.sweattrails.api;
var ___ = com.sweattrails.api.internal;

com.sweattrails.api.TypeError = class {
    constructor(t) {
        this.message = "Type error: " + t;
    }
}

com.sweattrails.api.dump = function(o, ...args) {
    if (args.length > 0) {
        console.log(...args);
    }
    console.dir(o)
}

/* -- M A N A G E R ------------------------------------------------------ */

com.sweattrails.api.Manager = class {
    constructor() {
        this.id = "APIManager";
        this.type = "manager";
        this.components = [];
        this.processors = [];
        this.objects = {}
        this.deferred = [];
        this.register(this);
    }

    registerObject(c) {
        const t = c.type;
        const what = t
            || (c.__proto__ && c.__proto__.constructor && c.__proto__.constructor.name)
            || "unknown";
        if (!c.type) {
            c.type = what;
        }
        const name = c.id || c.name;
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
    }

    register(c) {
        this.registerObject(c);
        this.components.push(c);
        if (c.container && c.render && this.objects.TabManager) {
            const elem = c.container;
            let renderables = this.objects.TabManager.renderables;
            for (let p = elem; p; p = p.parentNode) {
                if (p.className === "tabpage") {
                    renderables = this.tab[p.id.substring(5)].renderables;
                    break;
                }
            }
            renderables.push(c);
        }
        console.log("%s: registered %s, type %s (%d)", this.id, c.id, c.type, this.components.length);
        return this;
    }

    processor(tagname, processor) {
        this.register(processor);
        this.processors.push({ tagname, processor });
    }

    get(id) {
        return this.objects[id];
    }

    all(type) {
        return this[type];
    }

    onstarted(f) {
        this.deferred.push(f);
    }

    process() {
        this.processors.forEach((p) => {
            const tagname = p.tagname;
            const processor = p.processor;
            const elements = document.getElementsByTagNameNS(com.sweattrails.api.xmlns, tagname);
            this.log(this, `build(${tagname}): found ${elements.length} elements`);
            for ( ; elements.length > 0; ) {
                const element = elements[0];
                const parent = element.parentNode;
                processor.process(element);
                parent.removeChild(element);
            }
        });
    }

    start() {
        this.deferred.forEach((deferred) => deferred());
    }

    run() {
        this.dispatch("load");
        this.log(this, "Loaded");
        this.dispatch("build");
        this.log(this, "Built");
        this.process();
        this.log(this, "Processed");
        this.dispatch("start");
        this.log(this, "Started");
    }

    render(id) {
        this.executeOn(id, "render");
    }

    executeOn(id, func) {
        const obj = this.objects[id];
        if (obj && obj[func]) {
            obj[func]();
        }
    }

    dispatch(d) {
        this.components.forEach((c) => {
            if (c[d]) {
                c[d]();
            }
        });
    }

    async(obj) {
        if (typeof(this.asyncQueue) === "undefined") {
            this.asyncQueue = [];
        }
        if (this.asyncQueue.length === 0) {
            setInterval(com.sweattrails.api.internal.asyncHandler, 0);
        }
        this.asyncQueue.push(obj);
    }


    objectlabel(obj) {
        let o = "";
        if (obj) {
            if (obj.type) {
                o = obj.type + ((obj.id || obj.name) ? ("(" + (obj.id || obj.name) + ")") : "");
            } else {
                o = obj.toString();
            }
            o += ": ";
        }
        return o;
    }

    log(obj, msg, ...args) {
        let logargs = [this.objectlabel(obj) + msg];
        if (args.length > 0) {
            logargs = logargs.concat(args);
        }
        console.log(...logargs);
    }

    assert(obj, condition, msg) {
        console.assert(condition, this.objectlabel(obj), msg);
    }

    dump(...args) {
        com.sweattrails.api.dump(...args);
    }
}

com.sweattrails.api.STManager = new com.sweattrails.api.Manager();

com.sweattrails.api.internal.asyncHandler = function() {
    for (let obj = $$.asyncQueue.pop(); obj; obj = $$.asyncQueue.pop()) {
        obj.onASync && obj.onASync();
    }
}

function $(id) {
    return com.sweattrails.api.STManager.get(id);
}

function _$(type) {
    return com.sweattrails.api.STManager.all(type);
}

var $$ = __.STManager;
var _ = $$.objects;

/* -- B A S I C T A B ---------------------------------------------------- */

com.sweattrails.api.BasicTab = class {
    constructor() {
        this.onSelect = null;
        this.onUnselect = null;
        this.onDraw = null;
    }
}

/* -- T A B -------------------------------------------------------------- */

com.sweattrails.api.internal.Tab = class {
    constructor(code, label, elem) {
        this.type = "tab";
        this.impl = null;
        if (elem) {
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
    }

    select() {
        if (this.impl && this.impl.onSelect) {
            this.impl.onSelect();
        }
        this.renderables.forEach((renderable) => {
            if (!renderable.container.hidden || (renderable.container.className === "tabpage")) {
                renderable.render();
            }
        });
        this.header.className = "tab_selected";
        this.href.className = "whitelink";
        this.page.hidden = false;
    }

    unselect() {
        if (this.impl && this.impl.onUnselect) {
            impl.onUnselect();
        }
        this.header.className = "tab";
        this.href.className = "greylink";
        this.page.hidden = true;
    }
}

/* -- T A B M A N A G E R ------------------------------------------------ */

com.sweattrails.api.TabManager = class {
    constructor() {
        if (com.sweattrails.api.tabManager) {
            alert("TabManager is a singleton!");
            return;
        }
        this.id = "TabManager";
        this.type = "manager";
        com.sweattrails.api.STManager.register(this);
        this.renderables = [];
        this.tabs = {}
        this.firsttab = null;

        this.select = function(code, ev) {
            this.selectTab(code); ev.
            stopPropagation();
        }
    }

    build() {
        this.pagebox = document.getElementById("pagebox");
        if (!this.pagebox) return;
        const tb = this.pagebox.getElementsByTagNameNS(com.sweattrails.api.xmlns, "tabs");
        if (tb && (tb.length > 0)) {
            var tabs_elem = tb[0];
            var tabs = getChildrenByTagNameNS(tabs_elem, com.sweattrails.api.xmlns, "tab");
            $$.log(this, `Found ${tabs.length} tabs`);
            for (var tabix = 0; tabix < tabs.length; tabix++) {
                var tab_elem = tabs[tabix];
                var tab = this.addTabFromElem(tab_elem);
                this.firsttab = this.firsttab || tab;
                tabs_elem.removeChild(tab_elem);
            }
        }
    }

    start() {
        const pw = document.getElementById("page_pleasewait");
        if (pw) {
            pw.hidden = true;
        }
        this.renderables.forEach((renderable) => {
            if (renderable && renderable.render) {
                renderable.render();
            }
        });
        if (this.firsttab) {
            this.selectTab(this.firsttab.code);
        }
    }

    addTabFromElem(elem) {
        const tab = this.addTab(new com.sweattrails.api.internal.Tab(elem.getAttribute("code"), elem.getAttribute("label"), elem));
        if (tab) {
            while (elem.childNodes.length > 0) {
                tab.page.appendChild(elem.childNodes[0]);
            }
        }
        return tab;
    }

    addTab(tab) {
        $$.log(this, `addTab(${tab.code})`);
        if (!tab.impl || !tab.impl.onDraw || tab.impl.onDraw()) {
            this.drawTab(tab);
            this.tabs[tab.code] = tab;
            return tab;
        } else {
            $$.log(this, `Tab ${tab.code} hidden`);
            return null;
        }
    }

    drawTab(tab) {
        $$.log(this, `Tab ${tab.code} visible`);
        tab.manager = this;
        const tabbox = document.getElementById("tabbox");
        const span = document.createElement("span");
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
        if (tab.draw) {
            tab.draw();
        }
    }

    selectTab(code) {
        $$.log(this, `selectTab(${code})`);
        const newtab = this.tabs[code];
        if (newtab) {
            Object.values(this.tabs)
                .filter((tab) => (tab.header.className === "tab_selected") && (tab.code !== code))
                .forEach((tab) => { tab.unselect()});
            if (newtab.header.className !== 'tab_selected') {
                newtab.select();
            }
            return true;
        }
        return false;
    }
}

com.sweattrails.api.tabManager = new com.sweattrails.api.TabManager();

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.DataBridge = class {
    constructor(getvalue = null, setvalue = getvalue) {
        this.get = getvalue;
        this.set = setvalue;
    }

    get get() {
        return this._getvalue;
    }

    set get(getvalue) {
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

    get set() {
        return this._setvalue
    }

    set set(setvalue) {
        this._setvalue = setvalue;
        this._setter = null;
        this._setprop = null;
        if (setvalue) {
            if (typeof(setvalue) === "string") {
                if (setvalue.startsWith("=")) {
                    // -- no-op.
                } else if (setvalue.endsWith("()")) {
                    this._setter = __.getfunc(g.substring(0, g.length() - 2), null, this);
                } else {
                    this._setprop = setvalue;
                }
            } else if (typeof(setvalue) === "function") {
                this._setter = setvalue.bind(this);
            } else {
                // -- no-op.
            }
        }
    }

    setValue(object, value) {
        try {
            if (this._setter) {
            	this._setter(object, value);
            } else if (this._setprop) {
                __.setvar(this._setprop, value, object);
            }
            __.dump(object, "%s.setValue(%s)", this, value);
        } catch (e) {
            console.trace("Exception in Databridge.setValue: " + e);
            __.dump(object, "bridge.set: " + this.set + " object =");
            throw e;
        }
    }

    getValue(object) {
        try {
            if (this._getstatic) {
                return this._getstatic;
            } else if (this._getter) {
                return this._getter(object, (arguments.length > 1) ? arguments[1] : window);
            } else if (this._getprop !== null) {
                return __.getvar(this._getprop, object);
            } else {
                return null;
            }
        } catch (e) {
            console.trace("Exception in Databridge.getValue: " + e);
            __.dump(object, "bridge.get: " + this.get + " object =");
            throw e;
        }
    }

    clear(object) {
        if (this._setter) {
        	this._setter(object, null);
        } else if (this._setprop) {
            __.clearvar(this._setprop, object);
        }
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.walkname = function(name, ns = window) {
    const ret = { ns, component: null };
    if (!ret.ns) {
        ret.ns = window;
    }
    return name.split(".").reduce((ctx, c) => {
        if (ctx.component) {
            if (!ctx.component in ctx.ns) {
                ctx.ns[ctx.component] = {};
            }
            ctx.ns = ctx.ns[ctx.component];
        }
        ctx.component = c.trim();
        return ctx;
    }, ret);
}

com.sweattrails.api.getvar = function(name, ns = window) {
    const walk = { ns, component: null };
    if (!walk.ns) {
        walk.ns = window;
    }
    name.split(".").reduce((ctx, c) => {
        if (ctx.ns) {
            if (ctx.component) {
                ctx.ns = ctx.ns[ctx.component] || null;
            }
            ctx.component = c.trim();
        }
        return ctx;
    }, walk);
    return (walk.ns) ? walk.ns[walk.component] : null;
}

getvar = __.getvar;

com.sweattrails.api.clearvar = function(name, ns = null) {
    const wn = ___.walkname(name, ns);
    if (wn.ns && wn.component) {
        wn.ns[wn.component] = null;
    }
    return ns;
}

com.sweattrails.api.setvar = function (name, value, ns = window) {
    const wn = ___.walkname(name, ns);
    if (wn.ns && wn.component) {
        if ((wn.component in wn.ns) && (wn.ns[component] !== null)) {
            const oldval = wn.ns[wn.component];
            if (Array.isArray(oldval)) {
                oldval.push(value);
            } else {
                wn.ns[wn.component] = [oldval, value];
            }
        } else {
            wn.ns[wn.component] = value;
        }
    }
    return wn.ns;
}

setvar = __.setvar;

com.sweattrails.api.getfunc = function (func, ns = window, thisObj = null) {
    let f = null;
    if (typeof(func) === "function") {
        f = func;
    } else {
        const v = __.getvar(func, ns);
        f = (typeof(v) === "function") && v;
    }
    if (f && thisObj) {
        f = f.bind(thisObj);
    }
    return f;
}

getfunc = __.getfunc;

com.sweattrails.api.mixin = function(cls, mixin) {
    if (mixin.mixin && (typeof(mixin.mixin) === "function")) {
        mixin.mixin(cls);
    } else {
        Object.entries(mixin)
              .filter(([name, value]) => typeof(value) === 'function')
              .forEach(([name, f]) => { cls.prototype[name] = f });
    }
    return cls;
}

/**
 * Builder - Abstract base class for element builders.
 */

com.sweattrails.api.BuilderFlags = {}
com.sweattrails.api.BuilderFlags.Int = 1;
com.sweattrails.api.BuilderFlags.Float = 2;
com.sweattrails.api.BuilderFlags.Function = 4;
com.sweattrails.api.BuilderFlags.Boolean = 8;

/* ----------------------------------------------------------------------- */

/**
 * GritObject mix-in.
 */

com.sweattrails.api.GritObject = {
    set(elem, tag, property = tag, flags = 0) {
        const val = elem.getAttribute(tag);
        let converted = undefined;
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
        if (converted === undefined) {
            converted = val;
        }
        if (typeof(property) === "function") {
            property.call(this, converted);
        } else if (val) {
            __.clearvar(property, this);
            __.setvar(property, converted, this);
        }
        return this;
    },

    buildChildren(elem, tag, childcls) {
        const elems = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, tag);
        Array.from(elems).forEach((elem) => {
            const child = new childcls(this);
            com.sweattrails.api.GritObject.mixin(child);
            child.build(elem);
        });
        return this;
    },

    setDataSource(ds) {
        if (ds) {
            this.datasource = ds;
            ds.addView(this);
        }
    },

    buildDataSource(elem) {
        if (_.DataSourceBuilder) {
            this.setDataSource(_.DataSourceBuilder.build(elem));
        }
    },

    mixin(cls) {
        const pr = cls.prototype;
        if (!pr.buildChildren) {
            pr.set = com.sweattrails.api.GritObject.set;
            pr.buildChildren = com.sweattrails.api.GritObject.buildChildren;
            if (pr.hasDataSource) {
                pr.setDataSource = com.sweattrails.api.GritObject.setDataSource;
                pr.buildDataSource = com.sweattrails.api.GritObject.buildDataSource;
            }
        }
        return cls;
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.Builder = class {
    constructor(tagname, objclass) {
        if (tagname) {
            this.type = "builder";
            this.name = tagname + "builder";
            this.objclass = objclass;
            __.mixin(this.objclass, com.sweattrails.api.GritObject);
            $$.processor(tagname, this);
        }
    }

    process(elem) {
        const name = elem.getAttribute("name");
        $$.log(this, `Building ${name}`);
        const obj = new this.objclass(elem.parentNode, name);
        obj.build(elem);
        if (obj.hasDataSource) {
            obj.buildDataSource(elem);
        }
    }
}

/* ----------------------------------------------------------------------- */

function getChildrenByTagNameNS(elem, ns, tagname) {
    const ret = [];
    Array.from(elem.childNodes)
         .filter(child => (child.namespaceURI === ns) && (child.localName === tagname))
         .forEach((child) => { ret.push(child); });
    return ret;
}

function hasChildWithTagNameNS(elem, ns, tagname) {
    return !!Array.from(elem.childNodes)
                  .find(child => (c.namespaceURI === ns) && (c.localName === tagname));
}

function processChildrenWithTagNameNS(elem, ns, tagname, f) {
    getChildrenByTagNameNS(elem, ns, tagname).forEach(f);
}

com.sweattrails.api.renderObject = function(elem, content) {
    let rendered;
    if (typeof(content) === "object") {
        if (content instanceof HTMLElement) {
            rendered = content;
        } else {
            if (typeof(content.render) === "function") {
                rendered = content.render();
            } else {
                rendered = String(content);
            }
        }
    } else {
        rendered = String(content);
    }
    if (typeof(rendered) === "string") {
        elem.innerHTML = rendered;
    } else if (!rendered) {
        elem.innerHTML = "&#160;";
    } else if (rendered instanceof HTMLElement) {
        elem.appendChild(rendered);
    } else {
        $$.log($$, `elem: ${elem}, typeof: ${typeof(elem)} rendering ${rendered}, type ${typeof(rendered)}`);
        throw TypeError(`Cannot include object ${rendered} in HTML document`);
    }
}


com.sweattrails.api.internal.DOMElementLike = class {
    constructor(obj = {}, ns, tagname) {
        this._ns = ns;
        this._tagname = tagname;
        this.object = obj;
    }

    getAttribute(attr) {
        if (typeof(this.object) !== "object") {
            return null;
        } else {
            let ret = (attr in this.object) ? this.object[attr] : null;
            if (["number", "string", "boolean"].indexOf(typeof(ret)) >= 0) {
                ret = ret.toString();
            } else {
                ret = null;
            }
            return ret;
        }
    }

    getAttributeNames() {
        return (typeof(this.object) === "object")
            ? Object.keys(this.object)
            : null;
    }

    get childNodes() {
        const ret = [];
        if (typeof(this.object) === "object") {
            Object.entries(this.object)
                  .forEach(([c, o]) => {
                      const o_arr = (Array.isArray(o)) ? o : [o];
                      o.forEach((child) => {
                          ret.push(new com.sweattrails.api.internal.DOMElementLike(child, this._ns, c));
                      })
                  });
        } else {
            ret.push(this.object.toString());
        }
        return ret;
    }

    get nodeValue() {
        return (typeof(this.object) !== "object")
            ? this.object.toString()
            : null;
    }

    get namespaceURI() {
        return this._ns;
    }

    get localName() {
        return this._tagname;
    }
}

getDOMElement = function(obj) {
    return (obj && obj.getAttribute)
        ? obj
        : new com.sweattrails.api.internal.DOMElementLike(obj, ST.xmlns, "object");
}

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
    let n = String(num);
    while (n.length < 2) n = "0" + n;
    return n;
}

function obj_to_datetime(obj) {
    if (obj && (typeof(obj) === 'object')) {
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

function date_to_obj(d = new Date()) {
    return {
        'year': d.getUTCFullYear(),
        'month': d.getUTCMonth() + 1,
        'day': d.getUTCDate()
    };
}

function time_to_obj(d = new Date()) {
    return {
        'hour': d.getUTCHours(),
        'minute': d.getUTCMinutes(),
        'second': d.getUTCSeconds()
    };
}

function datetime_to_obj(d = new Date()) {
    const ret = date_to_obj(d);
    Object.entries(time_to_obj(d))
          .forEach(([name, value]) => { ret[name] = value });
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
        const ampm = (d.hour < 12) ? "am" : "pm";
        const h = (d.hour + 12) % 12 || 12;
        return rpad(h, 2)  + ":" + rpad(d.minute, 2) + ampm;
    } else {
        return rpad(d.hour, 2)  + ":" + rpad(d.minute, 2);
    }
}

function format_elapsed_time(t) {
    let s = "";
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

function import_file(url, callback = null) {
    // Brute-force XSS denial:
    if ((url.indexOf("http://") === 0) || (url.indexOf("https://") === 0)) {
        return;
    }
    if (!document.head) {
        return;
    }
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = url;
    script.usercallback = callback;

    script.callback = function() {
        if (this.usercallback) {
            this.usercallback();
        }
        document.head.removeChild(this);
    };
    script.onreadystatechange = script.callback;
    script.onload = script.callback;
    script.onerror = function(err) {
        throw new URIError(`The script ${err.target.src} is not accessible.`);
    }
    document.head.appendChild(script);
}


// ------------------------------------------------------------------------
