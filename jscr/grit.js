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

/* -- V A R I A B L E  M A N I P U L A T I O N --------------------------- */

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

/* ------------------------------------------------------------------------ */

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
};

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

com.sweattrails.api.setprop = function(obj, prop, value) {
    if ((prop in obj) && (obj[prop] !== null)) {
        const oldval = obj[prop];
        if (Array.isArray(oldval)) {
            oldval.push(value);
        } else {
            obj[prop] = [oldval, value];
        }
    } else {
        obj[prop] = value;
    }
    return obj;
}

com.sweattrails.api.setvar = function (name, value, ns = window) {
    const wn = ___.walkname(name, ns);
    if (wn.ns && wn.component) {
        com.sweattrails.api.setprop(wn.ns, wn.component, value);
    }
    return wn.ns;
}

setvar = __.setvar;

com.sweattrails.api.getfunc = function (func, ns = window, thisObj = null) {
    let f = undefined;
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


/* ----------------------------------------------------------------------- */

/* -- GritObject mix-in and base object class ---------------------------- */

com.sweattrails.api.BuilderFlags = {}
com.sweattrails.api.BuilderFlags.Int = 1;
com.sweattrails.api.BuilderFlags.Float = 2;
com.sweattrails.api.BuilderFlags.Function = 4;
com.sweattrails.api.BuilderFlags.Boolean = 8;

com.sweattrails.api.GritObject = {
    set(options, tag, property = tag, flags = 0) {
        const val = options[tag];
        if (val) {
        let converted = undefined;
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
                converted = __.toBoolean(val);
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

    mixin(target) {
        if (!target.buildChildren) {
            target.set = com.sweattrails.api.GritObject.set;
            target.buildChildren = com.sweattrails.api.GritObject.buildChildren;
            if ('hasDatasource' in target) {
               target.setDataSource = com.sweattrails.api.GritObject.setDataSource;
            }
        }
        return target;
    }
}

/* -- P R O C E S S O R ------------------------------------------------------ */

com.sweattrails.api.Processor = class extends com.sweattrails.api.GritObject {
    constructor() {
        super();
        this.processors = {};
    };

    processor(tagname, processor) {
        if (processor) {
            this.processors[tagname] = processor;
        }
        return this.processors[tagname];
    };

    parseOptions(elem, suboptions) {
        const sub = suboptions || this.suboptions;

        /*
         * Build an object out of all the children of elem with tagname
         * <st:option> or <st:value> and a 'name' attribute. The 'name'
         * attribute will be the property name, the value will be either
         * the 'value' attribute, if it exists, or the text content of the
         * element.
         *
         * if the element tag name is present in the 'suboptions' template
         * object, descent into the element and add the return object to
         * the object we're building with as property name the tag name.
        */
        const ret = Array.from(elem.childNodes).reduce((accum, c) => {
            const n = c.localName;
            const ns = c.namespaceURI;
            if ((ns === com.sweattrails.api.xmlns)
                    && (['option', 'value', 'choice'].indexOf(n) >= 0)
                    && (c.getAttribute("name") || c.getAttribute('key'))) {
                com.sweattrails.api.setprop(accum, c.getAttribute("name") || c.getAttribute('key'),
                    c.getAttribute("value") || c.textContent);
            } else if (sub && (typeof(sub[n]) !== "undefined")) {
                accum[n] = this.parseOptions(c, sub[n]);
                elem.removeChild(c);
            }
            return accum;
        }, { text: elem.textContent });

        /*
         * Set all attributes as properties on the return object.
         */
        Array.from(elem.getAttributeNames()).forEach((attr) => {
            ret[attr] = elem.getAttribute(attr);
        });__

        // Convert "[xxx, yyy]" string values to a array values.
        Object.entries(ret).forEach(([attr, value]) => {
            if (/^\[\ *(-?\d+\ *(,\ *-?\d+\ *)*)*\ *\]$/.test(value)) {
               ret[attr] = eval(value);
            }
        });
        return ret;
    }

    process(container, elem) {
        let e = null;
        let newobj = container;
        const n = e.localName;
        if (elem.namespaceURI === com.sweattrails.api.xmlns) {
            const parent = elem.parentNode;
            const options = this.parseOptions(elem);
            if (n === this.tagname) {
                newobj = (this.objclass)
                    ? __.instantiate(this.objclass, container, options)
                    : this.singleton
                if (newobj.hasDatasource && newobj.hasDatasource()) {
                    $$.processor('datasource').process(newobj, elem);
                }
                e = newobj.element;
            } else if (this.processors && this.processors[n]) {
                e = this.processors[n].process(container, elem);
            } else if (this.builders && this.builders[n]) {
                e = this.builders[n].bind(this)(container, options);
            } else if (this.isContainer && this.isContainer() && $$.processor(n)) {
                e = $$.processor(n).process(container, elem);
            }
            if (e) {
                if (!e.parentNode) {
                    parent.insertBefore(e, elem);
                }
                Array.from(elem.childNodes).forEach((c) => {
                    e.appendChild(c);
                });
            }
            parent.removeChild(elem);
        }
        Array.from(elem.childNodes).forEach((c) => {
            if (e) {
                e.appendChild(c);
            }
            this.process(newobj, c);
        });
        if ((c.namespaceURI === com.sweattrails.api.xmlns) && (n === this.tagname)) {
            newobj.build && newobj.build();
        }
        return e;
    }

    isContainer() {
        return false;
    }
};

/* -- M A N A G E R ------------------------------------------------------ */

com.sweattrails.api.Manager = class extends com.sweattrails.api.Processor {
    constructor() {
        super();
        this.id = "APIManager";
        this.type = "manager";
        this.components = [];
        this.objects = {}
        this.deferred = [];
        this.register(this);
        this.singleton = this;
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
        console.log("%s: registered %s, type %s (%d)", this.id, c.id, c.type, this.components.length);
        return this;
    }

    processor(tagname, processor) {
        if (processor) {
            this.register(processor);
        }
        super.processor(tagname, processor);
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

    start() {
        this.deferred.forEach((deferred) => deferred());
    }

    run() {
        this.dispatch("load");
        //this.dispatch("build");
        this.process(null, document.documentElement);
        this.dispatch("start");
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
        this[d] && this[d]();
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
            if (typeof(obj.componentlabel() === 'function')) {
                o = obj.componentlabel();
            } else if (obj.type) {
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

/* ----------------------------------------------------------------------- */

/**
 * Builder - Abstract base class for element builders.
 */

/* ----------------------------------------------------------------------- */

com.sweattrails.api.Builder = class extends __.Processor {
    constructor(tagname, objclass) {
        super();
        this.type = "builder";
        this.name = tagname + "builder";
        this.objclass = objclass;
        if (this.objclass) {
            __.mixin(this.objclass, com.sweattrails.api.GritObject);
        }
    }
};

/* -- W I D G E T -------------------------------------------------------- */

com.sweattrails.api.Widget = class extends com.sweattrails.api.GritObject {
    super(type, container = null, options = {}) {
        this.options = options;
        this.id = this.getId();
        this.type = type;
        this.container = container;
        this.element = null;
    };

    getId() {
        return this.options.name || this.options.id || this.options.code
    };

    set container(c) {
        this._container = c;
        if (c && c.addComponent) {
            c.addComponent(this);
        }
    };

    get container() {
        return this._container;
    }

    set parent(p) {
        if (this._element) {
            this._parent.removeChild(this._element);
            this._element = null;
        }
        this._parent = null;
        this._parentid = (p) ? p.id : null;
    }

    get parent() {
        if (!this._parent && this._parentid) {
            this._parent = document.getElementById(this._parentid);
        }
        return this._parent;
    }

    set element(e) {
        if (this._element) {
            this._element.parentNode.removeChild(this._element);
        }
        this._element = e;
    }

    get element() {
        return this._element;
    }

    log(...args) {
        $$.log(this, ...args);
    };

    assert(...args) {
        $$.assert(this, ...args);
    };

    dump(...args) {
        $$.dump(this, ...args);
    };
};

/* -- C O M P O N E N T -------------------------------------------------- */

com.sweattrails.api.Component = class extends com.sweattrails.api.Widget {
    super(type, container = null, options = {}) {
        super(type, container, options = {});
        this.components = [];
        $$.register(this);
    };

    addComponent(c) {
        this.components.push(c);
    };

    start() {
        [this, ...this.components].forEach((c) => { c.render && c.render() })
    }
};

// ------------------------------------------------------------------------
