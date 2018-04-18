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

if (typeof(Object.create) !== 'function') {
    Object.create = function(o) {
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
var G = com.sweattrails.api;
var G_int = com.sweattrails.api.internal;

com.sweattrails.api.TypeError = class {
    constructor(t) {
        this.message = "Type error: " + t;
    }
}

com.sweattrails.api.mixin = function(obj, mixin) {
    const target = (obj.prototype) ? obj.prototype : obj;
    if (mixin.mixin && (typeof(mixin.mixin) === "function")) {
        mixin.mixin(target);
    } else {
        Object.entries(mixin)
              .filter(([name, value]) => typeof(value) === 'function')
              .forEach(([name, f]) => { target[name] || (target[name] = f) });
    }
    return obj;
};

com.sweattrails.api.instantiate = function(fnc, ...args) {
    try {
        return fnc(...args);
    } catch(e) {
        return new fnc(...args);
    }
};

com.sweattrails.api.dump = function(o, ...args) {
    if (args.length > 0) {
        console.log(...args);
    }
    console.dir(o)
}

com.sweattrails.api.booleanValues = {
    "true": true,
    "false": false,
    "yes": true,
    "no": false,
    "y": true,
    "n": false,
}

com.sweattrails.api.toBoolean = function(v) {
    switch (typeof(v)) {
        case 'undefined':
        case 'boolean':
            return v;
        case 'string':
            if (!(v.toLowerCase() in __.booleanValues)) {
                return undefined;
            } else {
                return __.booleanValues[v.toLowerCase()];
            }
        case "number":
            return v != 0;
        case "object":
            return (v !== null);
        default:
            return false;
    }
};

com.sweattrails.api.isBoolean = function(v) {
    return typeof(__.toBoolean(v) === 'boolean');
};

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

com.sweattrails.api.getDOMElement = function(obj) {
    return (obj && (typeof(obj) === 'object') && (obj instanceof HTMLElement))
        ? obj
        : new com.sweattrails.api.internal.DOMElementLike(obj, ST.xmlns, "object");
};

/* ----------------------------------------------------------------------- */

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
        .forEach(([name, value]) => {
            ret[name] = value
        });
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
        return (true /* metric() */ ) ?
            rpad(d.day, 2) + "-" + rpad(d.month, 2) + "-" + d.year :
            rpad(d.month, 2) + "/" + rpad(d.day, 2) + "/" + d.year;
    } else {
        return null;
    }
}

function format_time(d) {
    if (false /* imperial() */ ) {
        const ampm = (d.hour < 12) ? "am" : "pm";
        const h = (d.hour + 12) % 12 || 12;
        return rpad(h, 2) + ":" + rpad(d.minute, 2) + ampm;
    } else {
        return rpad(d.hour, 2) + ":" + rpad(d.minute, 2);
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
    throw new URIError(`The script ${err.target.src} is not accessible.`);
    script.onload = script.callback;
    script.onerror = function(err) {}
    document.head.appendChild(script);
}
