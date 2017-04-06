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

com.sweattrails.api.internal.DataSource = function(id) {
    this.id = id;
    this.type = "datasource";
    $$.log(this, "Creating datasource");
    this._parameters = {};
    this._submitparams = {};
    this.view = [];
    this._sort = [];
    this._flags = [];
};

com.sweattrails.api.internal.DataSource.prototype.addView = function(v) {
    this.view.push(v);
};

com.sweattrails.api.internal.DataSource.prototype.addSort = function(column, ascending) {
    $$.log(this, "Adding sort %s %s", column, (ascending) ? "ASC" : "DESC");
    this._sort.push({"column": column, "ascending": ascending});
};

com.sweattrails.api.internal.DataSource.prototype.sortorder = function() {
    __.dump(this._sort, "sortorder()");
    return this._sort;
};
    
com.sweattrails.api.internal.DataSource.prototype.addFlag = function(name, value) {
    this._flags[name] = value;
};

com.sweattrails.api.internal.DataSource.prototype.flags = function() {
    return this._flags;
};
    
com.sweattrails.api.internal.DataSource.prototype.parameter = function(param, value) {
    $$.log(this, "parameter(%s = %s [%s])", param, value, typeof(value));
    this._parameters[param] = value;
};

com.sweattrails.api.internal.DataSource.prototype.parameters = function() {
    return this._parameters;
};

com.sweattrails.api.internal.DataSource.prototype.submitParameter = function(p, v) {
    this._submitparams[p] = v;
};

com.sweattrails.api.internal.DataSource.prototype.submitParameters = function() {
    return this._submitparams;
};

com.sweattrails.api.internal.DataSource.prototype.processData = function() {
    if (this.debug) {
        console.log("*** this.data:");
        ST.dump(this.data);
    }
    if (this.data && (!Array.isArray(this.data) || this.data.length)) {
        this.runCallbacks("onData", [this.data]);
        for (var n = this.next(); n; n = this.next()) {
            this.runCallbacks("renderData", [n]);
        }
        this.runCallbacks("onDataEnd", [this.data]);
    } else {
        this.runCallbacks("noData", []);
    }
};

com.sweattrails.api.internal.DataSource.prototype.next = function() {
    if (this.data) {
        if (Array.isArray(this.data)) {
            if (this.ix < this.data.length) {
                return this.data[this.ix++];
            } else {
                return null;
            }
        } else {
            this.object = (!this.object) ? this.data : null;
            if (this.object && ("key" in this.object)) {
                this.key = this.object.key;
            }
            if (this.debug && this.object) {
                $$.log(this, "next(): " + this.object);
                ST.dump(this.object);
            }
            this.data = null;
            return this.object;
        }
    } else {
        return null;
    }
};

com.sweattrails.api.internal.DataSource.prototype.reset = function() {
    if (arguments.length > 0) {
        this.data = arguments[0];
    }
    this.ix = 0;
    this.object = null;
    this.key = null;
};

com.sweattrails.api.internal.DataSource.prototype.execute = function() {
    this.reset();
    this.processData();
};

com.sweattrails.api.internal.DataSource.prototype.getObject = function() {
    return this.object;
};

com.sweattrails.api.internal.DataSource.prototype.setObject = function(obj) {
    this.object = obj || {};
    this.key = this.object.key || null;
};

com.sweattrails.api.internal.DataSource.prototype.getState = function() {
    var state = { object: this.object, key: this.key, ix: this.ix, data: this.data };
    if (typeof(this.extendState) === "function") {
        this.extendState(state)
    }
    return state;
};

com.sweattrails.api.internal.DataSource.prototype.setState = function(state) {
    this.object = state.object;
    this.key = state.key;
    this.ix = state.ix;
    this.data = state.data;
    if (typeof(this.restoreState) === "function") {
        this.restoreState(state)
    }
};

com.sweattrails.api.internal.DataSource.prototype.pushState = function(state) {
    if (typeof(this.states) === "undefined") {
    	this.states = [];
    }
    this.states.push(this.getState());
    this.setState(state);
};

com.sweattrails.api.internal.DataSource.prototype.popState = function() {
    if ((typeof(this.states) === "undefined") || (this.states.length === 0)) {
    	throw "Cannot pop from empty state stack"
    }
    return this.states.pop();
};

com.sweattrails.api.internal.DataSource.prototype.createObjectFrom = function(context) {
    if (!this.submitparams) {
	    this.submitparams = {};
    }
    this.object = null;
    if (this.factory) {
        this.object = this.factory(context);
    } else {
        this.object = {};
        for (p in this.submitparams) {
            if (!this.submitparams.hasOwnProperty(p)) {
                continue;
            }
            var v = this.submitparams[p];
            if (typeof(v) === "function") {
                this.object[p] = v(context);
            } else if (v.endsWith("()")) {
                var func = v.substring(0, v.length() - 2);
                var f = __.getfunc(func);
                if (f) {
                    this.object[p] = f(context);
                }
            } else if (v.startsWith("$")) {
                this.object[p] = context[v.substr(1)];
            } else {
                this.object[p] = v;
            }
        }
    }
    return this.object;
};

com.sweattrails.api.internal.DataSource.prototype.submit = function() {
};

com.sweattrails.api.internal.DataSource.prototype.runCallbacks = function(cb, args) {
    var ret = [];
    var r = this[cb] && this[cb].apply(this, args);
    if (r) {
    	ret.push(r);
    }
    for (var vix in this.view) {
        var v = this.view[vix];
        r = v[cb] && v[cb].apply(v, args);
        if (r) {
            ret.push(r);
        }
    }
    return (ret.length > 0) ? ((ret.length === 1) ? ret[0] : ret) : null;
};

com.sweattrails.api.internal.DataSource.prototype.onSuccess = function() {
    this.runCallbacks("onRequestSuccess", []);
};

com.sweattrails.api.internal.DataSource.prototype.onSubmitted = function() {
    this.runCallbacks("onDataSubmitted", []);
    var r = this.runCallbacks("onRedirect", [null, null]);
    if (r) {
        document.location = r;
    }
};

com.sweattrails.api.internal.DataSource.prototype.onRedirected = function(object, redir) {
    document.location = this.runCallbacks("onRedirect", [object, redir]) || redir;
};

com.sweattrails.api.internal.DataSource.prototype.onError = function(errorinfo, object) {
    this.runCallbacks("onDataError", [errorinfo, object]);
};

/**
 * JSONDataSource -
 */
com.sweattrails.api.JSONDataSource = function(contenttype, url, id) {
    com.sweattrails.api.internal.DataSource.call(this, (id) ? id : url);
    this.type = "JSONDataSource";
    $$.register(this);
    this.url = url;
    this.contenttype = contenttype;
    this.reset(null);
    this.async = true;
    return this;
};

com.sweattrails.api.JSONDataSource.prototype = new com.sweattrails.api.internal.DataSource("JSONDataSource prototype");

com.sweattrails.api.JSONDataSource.prototype.onJSONData = function(data) {
    $$.log(this, "onJSONData(data)");
    this.data = null;
    this.object = null;
    this.metadata = data.meta;
    data = data.data;
    this.reset(data);
    this.processData();
};

com.sweattrails.api.JSONDataSource.prototype.execute = function() {
    $$.log(this, "JSONDataSource.execute()");
    var submit = (arguments.length == 0) ? false : arguments[0];
    var contenttype = (submit) ? this.contenttype : com.sweattrails.api.HttpContentType.plain;
    this.request = com.sweattrails.api.getRequest(contenttype, this.url);
    this.request.datasource = this;
    this.setParameters(submit);
    this.request.execute();
};

com.sweattrails.api.JSONDataSource.prototype.setParameters = function(submit) {
    var obj = this.object || {};
    if (submit && this.key) {
        obj.key = this.key;
    }
    this.request.add(null, obj);
    this.request.add(null, this.parameters());
    if (!submit) {
        var order = this.sortorder();
        if (order.length) {
            this.request.add("_sortorder", order);
        }
    } else {
        this.request.add(null, this.submitParameters());
    }
    var flags = this.flags();
    if (flags) {
        this.request.add("_flags", flags);
    }
};

com.sweattrails.api.JSONDataSource.prototype.submit = function() {
    $$.log(this, "submit()");
    return this.execute(true);
};

/**
 * JSONDataSourceBuilder -
 */

com.sweattrails.api.JSONDataSourceBuilder = function() {
    this.id = "JSONDataSourceBuilder";
    this.type = "jsondatasourcebuilder"
    $$.registerObject(this);
};

com.sweattrails.api.JSONDataSourceBuilder.prototype.build = function(elem) {
    var url = elem.getAttribute("url");
    var contenttype = com.sweattrails.api.HttpContentType.json;
    if (elem.getAttribute("submit")) {
        var code = elem.getAttribute("submit");
        if (com.sweattrails.api.HttpContentType.hasOwnProperty(code)) {
            contenttype = com.sweattrails.api.HttpContentType[code]
        }
    }
    var ds = new com.sweattrails.api.JSONDataSource(contenttype, url, elem.getAttribute("dsid"));
    if (elem.getAttribute("async")) {
    	ds.async = elem.getAttribute("async") === "true";
    }
    ds.debug = false;
    if (elem.getAttribute("debug")) {
    	ds.debug = elem.getAttribute("debug") === "true";
    }
    var params = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "parameter");
    for (var ix = 0; ix < params.length; ix++) {
    	var p = params[ix];
        ds.parameter(p.getAttribute("name"), p.getAttribute("value"));
    }
    var sort = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "sort");
    for (ix = 0; ix < sort.length; ix++) {
    	var s = sort[ix];
        var o = s.getAttribute("order");
        ds.addSort(s.getAttribute("name"), o ? (o.indexOf("asc") === 0) : true);
    }
    var flags = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "flag");
    for (ix = 0; ix < flags.length; ix++) {
    	var f = flags[ix];
        var v = f.getAttribute("value") || true;
        ds.addFlag(f.getAttribute("name"), v);
    }
    params = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "submitparameter");
    for (ix = 0; ix < params.length; ix++) {
    	p = params[ix];
        ds.submitParameter(p.getAttribute("name"), p.getAttribute("value"));
    }
    return ds;
};

/**
 * CustomDataSource -
 * 
 * @param {Function,String} func Function used to query data.
 * @param {Function,String} submitfnc Function used to submit data. If ommitted 
 * or <b>null</b>, this datasource is read-only and can not be used to submit
 * data.
 */
com.sweattrails.api.CustomDataSource = function(func, submitfnc) {
    this.id = func;
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

com.sweattrails.api.CustomDataSource.prototype = new com.sweattrails.api.internal.DataSource("CustomDataSource prototype");

com.sweattrails.api.CustomDataSource.prototype.reset = function() {
    $$.log(this, "reset()");
    this.data = this.func();
    for (var ix = 0; ix < this.data.length; ix++) {
        $$.log(this, ix + ": " + this.data[ix].key + ", " + this.data[ix].value);
    }
    this.ix = 0;
    this.object = null;
};

com.sweattrails.api.CustomDataSource.prototype.submit = function() {
    $$.log(this, "submit()");
    this.data = null;
    if (this.submitfnc) {
    	this.submitfnc(this.object);
    }
};

/**
 * CustomDataSourceBuilder -
 */

com.sweattrails.api.CustomDataSourceBuilder = function() {
    this.id = "CustomDataSourceBuilder";
    this.type = "customdatasourcebuilder"
    $$.registerObject(this);
};

com.sweattrails.api.CustomDataSourceBuilder.prototype.build = function(elem) {
    var ds = null;
    if (elem.getAttribute("source")) {
    	ds = new com.sweattrails.api.CustomDataSource(elem.getAttribute("source"), elem.getAttribute("submit"));
    }
    return ds;
};

/**
 * StaticDataSource -
 */

com.sweattrails.api.StaticDataSource = function() {
    this.reset(null);
    this.data = [];
    this.view = [];
    this.keyname = "key";
    this.valname = "value";
    return this;
};

com.sweattrails.api.StaticDataSource.prototype = new com.sweattrails.api.internal.DataSource("StaticDataSource prototype");

com.sweattrails.api.StaticDataSource.prototype.value = function(key, value) {
    var obj = {};
    obj[this.keyname] = key;
    obj[this.valname] = value;
    this.data.push(obj);
};

/**
 * StaticDataSourceBuilder -
 */

com.sweattrails.api.StaticDataSourceBuilder = function() {
    this.id = "StaticDataSourceBuilder";
    this.type = "staticdatasourcebuilder"
    $$.registerObject(this);
};

com.sweattrails.api.StaticDataSourceBuilder.prototype.build = function(elem, values) {
    var ds = new com.sweattrails.api.StaticDataSource();
    if (elem.getAttribute("keyname")) {
    	ds.keyname = elem.getAttribute("keyname");
    }
    if (elem.getAttribute("valuename")) {
    	ds.valname = elem.getAttribute("valuename");
    }
    for (var ix = 0; ix < values.length; ix++) {
    	var v = values[ix];
        var val = v.getAttribute("text");
        if (!val) {
            val = v.nodeValue;
        }
        var key = v.getAttribute("key");
        if (!key) {
            key = val;
        }
        ds.value(key, val);
    }
    return ds;
};

/**
 * ObjectDataSource -
 */

com.sweattrails.api.ObjectDataSource = function(name) {
    this.reset(null);
    this.dsobject = __.getvar(name);
    this.view = [];
    this.data = this.dsobject;
    __.dump(this.data, "ObjectDataSource initialized:");
    return this;
};

com.sweattrails.api.ObjectDataSource.prototype =
    new com.sweattrails.api.internal.DataSource("ObjectDataSource prototype");

/**
 * ObjectDataSourceBuilder -
 */

com.sweattrails.api.ObjectDataSourceBuilder = function() {
    this.id = "ObjectDataSourceBuilder";
    this.type = "objectdatasourcebuilder"
    $$.registerObject(this);
};

com.sweattrails.api.ObjectDataSourceBuilder.prototype.build = function(elem) {
    return new com.sweattrails.api.ObjectDataSource(elem.getAttribute("object"));
};

/**
 * NullDataSource -
 */

com.sweattrails.api.NullDataSource = function() {
    this.reset(null);
    this.data = [];
    this.view = [];
    return this;
};

com.sweattrails.api.NullDataSource.prototype = new com.sweattrails.api.internal.DataSource("NullDataSource prototype");

/**
 * NullDataSourceBuilder -
 */

com.sweattrails.api.NullDataSourceBuilder = function() {
    this.id = "NullDataSourceBuilder";
    this.type = "nulldatasourcebuilder"
    $$.registerObject(this);
};

com.sweattrails.api.NullDataSourceBuilder.prototype.build = function() {
    return new com.sweattrails.api.NullDataSource();
};

/**
 * ProxyDataSource -
 * 
 * @param {object} proxy Object to obtain/submit data from and to. The object 
 * should have <tt>getProxyData()</tt> and <tt>submitProxyData(object)</tt>
 * methods.
 */
com.sweattrails.api.ProxyDataSource = function(proxy) {
    this.proxy = proxy;
    this.reset();
    return this;
};

com.sweattrails.api.ProxyDataSource.prototype = new com.sweattrails.api.internal.DataSource("ProxyDataSource prototype");

com.sweattrails.api.ProxyDataSource.prototype.reset = function() {
    this.data = this.proxy.getProxyData();
    this.ix = 0;
    this.object = null;
    this.key = null;
};

com.sweattrails.api.ProxyDataSource.prototype.submit = function() {
    this.proxy.pushProxyState(this.getState());
    this.proxy.submitProxyData && this.proxy.submitProxyData();
    this.proxy.popProxyState();
};

/**
 * DataSourceBuilder -
 */

com.sweattrails.api.DataSourceBuilder = function() {
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

com.sweattrails.api.DataSourceBuilder.prototype.build = function(elem, def_ds) {
    var ret = null;
    var datasources = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "datasource");
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
        var values = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "value");
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

com.sweattrails.api.dataSourceBuilder = new com.sweattrails.api.DataSourceBuilder();
