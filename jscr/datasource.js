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

/* ----------------------------------------------------------------------- */

/**
 * DataSource -
 */

com.sweattrails.api.internal.DataSource = class {
    constructor(id) {
        this.id = id;
        this.type = "datasource";
        $$.log(this, "Creating datasource");
        this._parameters = {};
        this._submitparams = {};
        this.view = [];
        this._sort = [];
        this._flags = {};
    };

    addView(v) {
        this.view.push(v);
    };

    addSort(column, ascending) {
        $$.log(this, `Adding sort ${column} ${(ascending) ? 'ASC' : 'DESC'}`);
        this._sort.push({"column": column, "ascending": ascending});
    };

    sortorder() {
        __.dump(this._sort, "sortorder()");
        return this._sort;
    };

    addFlag(name, value) {
        this._flags[name] = value;
    };

    flags() {
        return this._flags;
    };

    parameter(param, value) {
        $$.log(this, `parameter(${param} = ${value} [${typeof(value)}])`);
        this._parameters[param] = value;
    };

    delParameter(param) {
        $$.log(this, `delParameter(${param} = ${this._parameters[param]})`);
        delete this._parameters[param];
    };

    parameters() {
        return this._parameters;
    };

    submitParameter(p, v) {
        this._submitparams[p] = v;
    };

    submitParameters() {
        return this._submitparams;
    };

    processData() {
        if (this.debug) {
            ST.dump(this.data, `${$$.objectlabel(this)}.processData()`);
        }
        if (this.data && (!Array.isArray(this.data) || this.data.length)) {
            this.runCallbacks("onData", this.data);
            for (let n = this.next(); n; n = this.next()) {
                this.runCallbacks("renderData", n);
            }
            this.runCallbacks("onDataEnd", this.data);
        } else {
            this.runCallbacks("noData");
        }
    };

    next() {
        if (this.data) {
            if (Array.isArray(this.data)) {
                this.object = (this.ix < this.data.length) ? this.data[this.ix++] : null;
            } else {
                this.object = this.data;
                this.data = null;
            }
            const ret = this.object;
            this.key = (this.object && ("key" in this.object)) ? this.object.key : null;
            if (this.debug && this.object) {
                $$.log(this, `next(): ${this.object}`);
                ST.dump(this.object);
            }
            return ret;
        } else {
            return null;
        }
    };

    reset(data) {
        if (data !== undefined) {
            this.data = data;
        }
        this.ix = 0;
        this.object = null;
        this.key = null;
    };

    execute() {
        this.reset();
        this.processData();
    };

    getObject() {
        return this.object;
    };

    setObject(obj) {
        this.object = obj || {};
        this.key = this.object.key || null;
    };

    getState() {
        const state = { object: this.object, key: this.key, ix: this.ix, data: this.data };
        if (typeof(this.extendState) === "function") {
            this.extendState(state)
        }
        return state;
    };

    setState(state) {
        this.object = state.object;
        this.key = state.key;
        this.ix = state.ix;
        this.data = state.data;
        if (typeof(this.restoreState) === "function") {
            this.restoreState(state)
        }
    };

    pushState(state) {
        if (typeof(this.states) === "undefined") {
        	this.states = [];
        }
        this.states.push(this.getState());
        this.setState(state);
    };

    popState() {
        if ((typeof(this.states) === "undefined") || (this.states.length === 0)) {
        	throw "Cannot pop from empty state stack"
        }
        return this.states.pop();
    };

    createObjectFrom(context) {
        if (!this.submitparams) {
    	    this.submitparams = {};
        }
        if (this.factory) {
            this.object = this.factory(context);
        } else {
            this.object = Object.entries(this.submitparams)
                                .reduce((obj, [p, v]) => {
                                    if (typeof(v) === "function") {
                                        obj[p] = v(context);
                                    } else if (v.endsWith("()")) {
                                        const f = __.getfunc(v.substring(0, v.length() - 2));
                                        if (f) {
                                            obj[p] = f(context);
                                        }
                                    } else if (v.startsWith("$")) {
                                        obj[p] = context[v.substr(1)];
                                    } else {
                                        obj[p] = v;
                                    }
                                    return obj;
                                }, {});
        }
        return this.object;
    };

    submit() {
    };

    runCallbacks(cb, ...args) {
        const ret = [];
        const r = this[cb] && this[cb](...args);
        if (r) {
        	ret.push(r);
        }
        this.view.reduce((ret, v) => {
            const r = v[cb] && v[cb](...args);
            if (r || (typeof(r) === 'boolean')) {
                ret.push(r);
            }
            return ret;
        }, ret);
        return (ret.length > 0) ? ((ret.length === 1) ? ret[0] : ret) : null;
    };

    onSuccess() {
        this.runCallbacks("onRequestSuccess");
    };

    onSubmitted() {
        this.runCallbacks("onDataSubmitted");
        const r = this.runCallbacks("onRedirect", null, null);
        if (r) {
            document.location = r;
        }
    };

    onRedirected(object, redir) {
        document.location = this.runCallbacks("onRedirect", object, redir) || redir;
    };

    onError(errorinfo, object) {
        this.runCallbacks("onDataError", errorinfo, object);
    };
}

/**
 * JSONDataSource -
 */
com.sweattrails.api.JSONDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor(contenttype, url, id) {
        super(id || url)
        this.type = "JSONDataSource";
        $$.register(this);
        this.url = url;
        this.contenttype = contenttype;
        this.reset(null);
        this.async = true;
        return this;
    };

    onJSONData(data) {
        $$.log(this, `onJSONData()`);
        this.data = null;
        this.object = null;
        this.metadata = data.meta || {};
        this.runCallbacks("onMetadata", this.metadata);
        data = data.data || {};
        this.reset(data);
        this.processData();
    };

    execute(submit = false) {
        $$.log(this, "JSONDataSource.execute()");
        const contenttype = (submit) ? this.contenttype : com.sweattrails.api.HttpContentType.plain;
        this.request = com.sweattrails.api.getRequest(contenttype, this.url);
        this.method && (this.request.method = this.method);
        this.request.datasource = this;
        this.setParameters(submit);
        this.request.execute();
    };

    setParameters(submit) {
        const obj = this.object || {};
        if (submit && this.key) {
            obj.key = this.key;
        }
        this.request.add(null, obj);
        this.request.add(null, this.parameters());
        if (!submit) {
            const order = this.sortorder();
            if (order.length) {
                this.request.add("_sortorder", order);
            }
        } else {
            this.request.add(null, this.submitParameters());
        }
        const flags = this.flags();
        if (flags) {
            this.request.add("_flags", flags);
        }
    };

    submit() {
        $$.log(this, "submit()");
        return this.execute(true);
    };
}

/**
 * JSONDataSourceBuilder -
 */

com.sweattrails.api.JSONDataSourceBuilder = class {
    constructor() {
        this.id = "JSONDataSourceBuilder";
        this.type = "jsondatasourcebuilder"
        $$.registerObject(this);
    };

    build(elem) {
        const url = elem.getAttribute("url");
        let contenttype = com.sweattrails.api.HttpContentType.json;
        if (elem.getAttribute("submit")) {
            const code = elem.getAttribute("submit");
            if (code in com.sweattrails.api.HttpContentType) {
                contenttype = com.sweattrails.api.HttpContentType[code]
            }
        }
        const ds = new com.sweattrails.api.JSONDataSource(contenttype, url, elem.getAttribute("dsid"));
        if (elem.getAttribute("async")) {
        	ds.async = elem.getAttribute("async") === "true";
        }
        if (elem.getAttribute("method")) {
            ds.method = elem.getAttribute("method");
        }
        ds.debug = false;
        if (elem.getAttribute("debug")) {
        	ds.debug = elem.getAttribute("debug") === "true";
        }
        if (elem.getAttribute("onmetadata")) {
            ds.onMetadata = __.getfunc(elem.getAttribute("onmetadata"));
        }
        processChildrenWithTagNameNS(elem, com.sweattrails.api.xmlns, "parameter",
            (p) => {
                ds.parameter(p.getAttribute("name"), p.getAttribute("value"));
            });
        processChildrenWithTagNameNS(elem, com.sweattrails.api.xmlns, "sort",
            (s) => {
                const o = s.getAttribute("order");
                ds.addSort(s.getAttribute("name"), o ? (o.indexOf("asc") === 0) : true);
            });
        processChildrenWithTagNameNS(elem, com.sweattrails.api.xmlns, "flag",
            (f) => {
                const v = f.getAttribute("value") || true;
                ds.addFlag(f.getAttribute("name"), v);
            });
        processChildrenWithTagNameNS(elem, com.sweattrails.api.xmlns, "submitparameter",
            (p) => {
                ds.submitParameter(p.getAttribute("name"), p.getAttribute("value"));
            });
        return ds;
    };
}

/**
 * CustomDataSource -
 *
 * @param {Function,String} func Function used to query data.
 * @param {Function,String} submitfnc Function used to submit data. If ommitted
 * or <b>null</b>, this datasource is read-only and can not be used to submit
 * data.
 */
com.sweattrails.api.CustomDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor(id, func, submitfnc) {
        super(id || ((typeof(func) === 'function') ? '[[custom]]' : func));
        this.type = "CustomDataSource";
        $$.register(this);
        this.data = null;
        this.view = [];
        this.func = (typeof(func) === 'function') ? func : __.getfunc(func);
        if (submitfnc) {
        	this.submitfnc = (typeof(submitfnc) === 'function') ? submitfnc : __.getfunc(submitfnc);
        }
        this.reset();
        return this;
    };

    reset() {
        $$.log(this, "reset()");
        this.data = this.func();
        this.ix = 0;
        this.object = null;
    };

    submit() {
        $$.log(this, "submit()");
        this.data = null;
        if (this.submitfnc) {
        	this.submitfnc(this.object);
        }
    };
}

/**
 * CustomDataSourceBuilder -
 */

com.sweattrails.api.CustomDataSourceBuilder = class {
    constructor() {
        this.id = "CustomDataSourceBuilder";
        this.type = "customdatasourcebuilder"
        $$.registerObject(this);
    };

    build(elem) {
        let ds = null;
        if (elem.getAttribute("source")) {
        	ds = new com.sweattrails.api.CustomDataSource(elem.getAttribute("id"), elem.getAttribute("source"), elem.getAttribute("submit"));
        }
        return ds;
    };
}

/**
 * StaticDataSource -
 */

com.sweattrails.api.StaticDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor(id) {
        super(id)
        this.reset(null);
        this.data = [];
        this.view = [];
        this.keyname = "key";
        this.valname = "value";
        return this;
    };

    value(key, value) {
        const obj = {};
        obj[this.keyname] = key;
        obj[this.valname] = value;
        this.data.push(obj);
    };
}

/**
 * StaticDataSourceBuilder -
 */

com.sweattrails.api.StaticDataSourceBuilder = class {
    constructor() {
        this.id = "StaticDataSourceBuilder";
        this.type = "staticdatasourcebuilder"
        $$.registerObject(this);
    };

    build(elem, values) {
        const ds = new com.sweattrails.api.StaticDataSource(elem.getAttribute("id"));
        if (elem.getAttribute("keyname")) {
        	ds.keyname = elem.getAttribute("keyname");
        }
        if (elem.getAttribute("valuename")) {
        	ds.valname = elem.getAttribute("valuename");
        }
        values.forEach((v) => {
            let val = v.getAttribute("text");
            if (!val) {
                val = v.textContent;
            }
            let key = v.getAttribute("key");
            if (!key) {
                key = val;
            }
            ds.value(key, val);
        });
        return ds;
    };
}

/**
 * ObjectDataSource -
 */

com.sweattrails.api.ObjectDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor(name) {
        super(name);
        this.reset(null);
        this.dsobject = __.getvar(name);
        this.view = [];
        this.data = this.dsobject;
        __.dump(this.data, "ObjectDataSource initialized:");
        return this;
    };
}

/**
 * ObjectDataSourceBuilder -
 */

com.sweattrails.api.ObjectDataSourceBuilder = class {
    constructor() {
        this.id = "ObjectDataSourceBuilder";
        this.type = "objectdatasourcebuilder"
        $$.registerObject(this);
    };

    build(elem) {
        return new com.sweattrails.api.ObjectDataSource(elem.getAttribute("object"));
    };
}

/**
 * NullDataSource -
 */

com.sweattrails.api.NullDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor() {
        super("null");
        this.reset(null);
        this.data = [];
        this.view = [];
        return this;
    };
}

/**
 * NullDataSourceBuilder -
 */

com.sweattrails.api.NullDataSourceBuilder = class {
    constructor() {
        this.id = "NullDataSourceBuilder";
        this.type = "nulldatasourcebuilder"
        $$.registerObject(this);
    };

    build() {
        return new com.sweattrails.api.NullDataSource();
    };
}

/**
 * ProxyDataSource -
 *
 * @param {object} proxy Object to obtain/submit data from and to. The object
 * should have <tt>getProxyData()</tt> and <tt>submitProxyData(object)</tt>
 * methods.
 */
com.sweattrails.api.ProxyDataSource = class extends com.sweattrails.api.internal.DataSource {
    constructor(proxy) {
        super("[[proxy]]");
        this.proxy = proxy;
        this.reset();
        return this;
    };

    reset() {
        this.data = this.proxy.getProxyData();
        this.ix = 0;
        this.object = null;
        this.key = null;
    };

    submit() {
        this.proxy.pushProxyState(this.getState());
        this.proxy.submitProxyData && this.proxy.submitProxyData();
        this.proxy.popProxyState();
    };
}

/**
 * DataSourceBuilder -
 */

com.sweattrails.api.DataSourceBuilder = class {
    constructor() {
        this.id = "DataSourceBuilder";
        this.type = "datasourcebuilder"
        $$.registerObject(this);
        this.jsonbuilder = new com.sweattrails.api.JSONDataSourceBuilder();
        this.staticbuilder = new com.sweattrails.api.StaticDataSourceBuilder();
        this.objectbuilder = new com.sweattrails.api.ObjectDataSourceBuilder();
        this.custombuilder = new com.sweattrails.api.CustomDataSourceBuilder();
        this.nullbuilder = new com.sweattrails.api.NullDataSourceBuilder();
        return this;
    };

    build(elem, def_ds) {
        let ret = null;
        const datasources = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "datasource");
        if (datasources && (datasources.length > 0)) {
        	elem = datasources[0];
        }
        if (elem.getAttribute("url")) {
        	ret = this.jsonbuilder.build(elem);
        } else if (elem.getAttribute("object")) {
        	ret = this.objectbuilder.build(elem);
        } else if (elem.getAttribute("source")) {
        	ret = this.custombuilder.build(elem);
        } else {
            let values = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "value");
            if (values.length === 0) {
                values = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "choices");
            }
            if (values.length > 0) {
                ret = this.staticbuilder.build(elem, values);
            } else {
                ret = (def_ds) ? def_ds : this.nullbuilder.build(elem);
            }
        }
        if (ret) {
            ret.debug = elem.getAttribute("debug");
        	if (elem.getAttribute("ondata")) {
                ret.onData = __.getfunc(elem.getAttribute("ondata"));
        	}
        	if (elem.getAttribute("nodata")) {
                ret.noData = __.getfunc(elem.getAttribute("nodata"));
        	}
        	if (elem.getAttribute("renderdata")) {
                ret.renderData = __.getfunc(elem.getAttribute("renderdata"));
        	}
        	if (elem.getAttribute("ondataend")) {
                ret.onDataEnd = __.getfunc(elem.getAttribute("ondataend"));
        	}
        	if (elem.getAttribute("onerror")) {
                ret.onDataError = __.getfunc(elem.getAttribute("ondataerror"));
        	}
        	if (elem.getAttribute("onsubmitted")) {
                ret.onDataSubmitted = __.getfunc(elem.getAttribute("onsubmitted"));
        	}
        }
        return ret;
    };
}

com.sweattrails.api.dataSourceBuilder = new com.sweattrails.api.DataSourceBuilder();
