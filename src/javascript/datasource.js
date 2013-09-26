com.sweattrails.api.JSONRequest = function(url) {
    this.url = url;
    if (arguments.length > 1) {
        this.onSuccess = arguments[1];
    }
    if (arguments.length > 2) {
        this.onError = arguments[2];
    }
    this.params = {};
    this.json = true;
    return this;
};

com.sweattrails.api.JSONRequest.prototype.parameter = function(param, value) {
    this.params[param] = value;
};

com.sweattrails.api.getHttpRequest = function(jsonRequest) {
    var httpRequest = getXmlHttpRequest();
    if (!httpRequest) {
        return false;
    }

    httpRequest.request = jsonRequest;
    httpRequest.onreadystatechange = function() {
        if (this.readyState === 4) {
            this.request.log("Received response. Status " + this.status);
            var object = {};
            if (this.responseText !== "") {
                try {
                    object = JSON.parse(this.responseText);
                } catch (e) {
                    // Ignored
                }
            }
            if ((this.status >= 200 && this.status <= 200) || this.status === 304) {
                var redir = this.getResponseHeader("ST-JSON-Redirect");
                if (redir && this.request.onRedirect) {
                    this.request.onRedirect(object, redir);
                } else {
                    var posted = this.request.post;
                    this.request.post = false;
                    this.request.object = null;
                    this.request.params = [];
                    this.request.onSuccess(object);
                    if (posted && this.request.onSubmitted) {
                        this.request.onSubmitted();
                    }
                }
                this.request.semaphore = 0;
                this.request.log("response processed");
            } else {
                this.request.log("  *** XMLHttp Error *** " + this.status);
                if (this.request.onError) {
                    this.request.onError(this.status, object);
                } else {
                    alert("XMLHttpRequest for " + this.request.url + " returned " + this.status);
                }
                this.request.semaphore = this.status;
                this.request.log("Error processed");
            }
        }
    };
    return httpRequest;
};

com.sweattrails.api.JSONRequest.prototype.execute = function() {
    var httpRequest = com.sweattrails.api.getHttpRequest(this);
    if (!httpRequest) {
        return false;
    }

    this.semaphore = 1;
    if (this.datasource && ("async" in this.datasource)) {
        this.async = this.datasource.async;
    }
    if (!("async" in this)) this.async = true;
    if (!this.post) this.post = false;
    url = this.url;
    if (typeof(key) !== "undefined") {
        url = url.replace('$$', key);
    }
    url = url.replace(/\$([\w]+)/g, function() {
        return getvar(arguments[1]);
    });
    if (this.json) {
        this.log(((this.post) ? "POST " : "GET " ) + url + " as JSON data with body\n" + this.body);
        httpRequest.open((this.post) ? "POST" : "GET", url, this.async);
        httpRequest.setRequestHeader("ST-JSON-Request", (this.post) ? "true": this.body);
        httpRequest.send((this.post) ? this.body : null);
    } else {
        var parameters = new FormData();
        for (p in this.params) {
            parameters.append(p, this.params[p]);
        }
        this.log(((this.post) ? "POST " : "GET " ) + url + " as form data with " + this.params.length + " parameters");
        httpRequest.open((this.post) ? "POST" : "GET", url, this.async);
        httpRequest.send(parameters);
    }
    return true;
};

com.sweattrails.api.JSONRequest.prototype.onSuccess = function(data) {
    this.data = data;
    if (this.datasource && this.datasource.onJSONData) {
    	this.datasource.onJSONData(data);
    }
};

com.sweattrails.api.JSONRequest.prototype.onSubmitted = function() {
    if (this.datasource && this.datasource.onSubmitted) {
    	this.datasource.onSubmitted();
    }
};

com.sweattrails.api.JSONRequest.prototype.onRedirect = function(object, redir) {
    if (this.datasource && this.datasource.onRedirected) {
    	this.datasource.onRedirected(object, redir);
    }
};

com.sweattrails.api.JSONRequest.prototype.onError = function(code, object) {
    this.log("HTTP Error " + code);
    this.post = false;
    if (this.datasource && this.datasource.onError) {
        this.log("Calling onError on datasource");
    	this.datasource.onError(code, object);
    }
};

com.sweattrails.api.JSONRequest.prototype.log = function(msg) {
    this.datasource && $$.log(this.datasource, "XMLHttp - " + msg);
};

/**
 * DataSource -
 */

com.sweattrails.api.internal.DataSource = function() {
};

com.sweattrails.api.internal.DataSource.prototype.addView = function(v) {
    if (!this.view) {
    	this.view = [];
    }
    this.view.push(v);
};

com.sweattrails.api.internal.DataSource.prototype.addSort = function(column, ascending) {
    if (typeof(this._sort) === "undefined") {
    	this._sort = [];
    }
    console.log("addSort(" + column + ", " + ascending + ")");
    this._sort.push({"column": column, "ascending": ascending});
};

com.sweattrails.api.internal.DataSource.prototype.sortorder = function() {
    if (typeof(this._sort) === "undefined") {
    	this._sort = [];
    }
    return this._sort;
};
    
com.sweattrails.api.internal.DataSource.prototype.addFlag = function(name, value) {
    if (typeof(this._flags) === "undefined") {
    	this._flags = {};
    }
    console.log("addFlag(" + name + ", " + value + ")");
    this._flags[name] = value;
};

com.sweattrails.api.internal.DataSource.prototype.flags = function() {
    if (typeof(this._flags) === "undefined") {
    	this._flags = null;
    }
    return this._flags;
};
    
com.sweattrails.api.internal.DataSource.prototype.submitParameter = function(p, v) {
    if (!this.submitparams) {
        this.submitparams = {};
    }
    this.submitparams[p] = v;
};

com.sweattrails.api.internal.DataSource.prototype.processData = function() {
    if (!this.view) {
    	this.view = [];
    }
    this.runCallbacks("onData", [this.data]);
    if (!this.data || (Array.isArray(this.data) && !this.data.length)) {
        this.runCallbacks("noData", []);
    } else {
        for (var n = this.next(); n; n = this.next()) {
            this.runCallbacks("renderData", [n]);
        }
    }
    this.runCallbacks("onDataEnd", [this.data]);
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
                var dump = function(indent, o) {
                    for (var k in o) {
                        if (typeof(o[k]) === "object") {
                            console.log(indent + k + ":");
                            dump(indent + "  ", o[k]);
                        } else {
                            console.log(indent + k + ": " + o[k]);
                        }
                    }                    
                };
                dump("  ", this.object);
            }
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
            var v = this.submitparams[p];
            if (typeof(v) === "function") {
                this.object[p] = v(context);
            } else if (v.endsWith("()")) {
                func = v.substring(0, v.length() - 2);
                f = getfunc(func);
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

com.sweattrails.api.internal.DataSource.prototype.onSubmitted = function() {
    this.runCallbacks("onDataSubmitted", []);
    var r = this.runCallbacks("onRedirect", [null, null]);
    if (r) {
        document.location = r;
    }
};

com.sweattrails.api.internal.DataSource.prototype.onRedirected = function(object, redir) {
    var r = this.runCallbacks("onRedirect", [object, redir]) || redir;
    document.location = r;
};

com.sweattrails.api.internal.DataSource.prototype.onError = function(errorinfo, object) {
    this.runCallbacks("onDataError", [errorinfo, object]);
};

/**
 * JSONDataSource -
 * 
 * @param {String} url
 */
com.sweattrails.api.JSONDataSource = function(url) {
    this.id = url;
    this.type = "JSONDataSource";
    $$.register(this);
    this.reset(null);
    this.async = true;
    this.request = new com.sweattrails.api.JSONRequest(url);
    this.request.datasource = this;
    this.submitAsJSON = true;
    return this;
};

com.sweattrails.api.JSONDataSource.prototype = new com.sweattrails.api.internal.DataSource();

com.sweattrails.api.JSONDataSource.prototype.parameter = function(param, value) {
    this.request.parameter(param, value);
};

com.sweattrails.api.JSONDataSource.prototype.onJSONData = function(data) {
    $$.log(this, "onJSONData(data)");
    this.reset(data);
    this.processData();
};

com.sweattrails.api.JSONDataSource.prototype.execute = function() {
    $$.log(this, "onJSONData(execute)");
    this.data = null;
    this.setJSONParameters(false);
    this.request.execute();
};

com.sweattrails.api.JSONDataSource.prototype.addObject = function(obj, prefix) {
    prefix = prefix || "";
    for (var p in obj) {
        var v = obj[p];
        if (typeof(v) === "object") {
            this.addObject(prefix + p + ".", v);
        } else if (typeof(v) === "function") {
            continue;
        } else {
            this.parameter(prefix + p, v);
        }
    }
};

com.sweattrails.api.JSONDataSource.prototype.setJSONParameters = function(obj, submit) {
    obj = obj || {}
    var o = {};
    for (a in obj) {
        o[a] = obj[a];
    }
    function build_param_obj(src, target) {
        for (var p in src) {
            var v = src[p];
            var f = null;
            if (typeof(v) === "function") {
                f = v;
            } else if ((typeof(v) === "string") && v.endsWith("()")) {
                f = getfunc(v.substring(0, v.length() - 2));
                this.request.params[p] = f;
            }
            if (f) {
                v = f();
            } else if (v.indexOf("$") === 0) {
                v = getvar(v.substr(1));
            }
            setvar(p, v, target);
        }
    }
    if (!submit) {
        build_param_obj(this.request.params, o);
        if (this.sortorder().length) {
            o["_sortorder"] = this.sortorder();
        }
    } else {
        if (this.key) o.key = this.key;
        build_param_obj(this.request.submitparams, o);
    }
    if (this.flags()) {
        o["_flags"] = this.flags();
    }
    this.request.body = JSON.stringify(o);    
}

com.sweattrails.api.JSONDataSource.prototype.setParameters = function(submit) {
    var obj = this.object || {};
    $$.log(this, "setParameters - json: " + this.submitAsJSON + " object " + JSON.stringify(obj));
    if (this.submitAsJSON) {
        this.setJSONParameters(obj, submit);
    } else {
        this.addObject(obj);
    }
};


com.sweattrails.api.JSONDataSource.prototype.submit = function() {
    $$.log(this, "submit()");
    this.data = null;
    this.request.post = true;
    this.setParameters(true);
    this.request.json = this.submitAsJSON;
    this.request.execute();
};

/**
 * JSONDataSourceBuilder -
 */

com.sweattrails.api.JSONDataSourceBuilder = function() {
};

com.sweattrails.api.JSONDataSourceBuilder.prototype.build = function(elem) {
    var ds = new com.sweattrails.api.JSONDataSource(elem.getAttribute("url"));
    this.submitAsJSON = true;
    if (elem.getAttribute("submit")) {
        ds.submitAsJSON = elem.getAttribute("submit") === "json";
    }
    if (elem.getAttribute("async")) {
    	ds.async = elem.getAttribute("async") === "true";
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
        ds.addSort(s.getAttribute("name"), o ? o.startsWith("asc") : true);
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
    this.func = (typeof(func) === 'function') ? func : getfunc(func);
    if (submitfnc) {
    	this.submitfnc = (typeof(submitfnc) === 'function') ? submitfnc : getfunc(submitfnc);
    }
    this.reset();
    return this;
};

com.sweattrails.api.CustomDataSource.prototype = new com.sweattrails.api.internal.DataSource();

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

com.sweattrails.api.StaticDataSource.prototype = new com.sweattrails.api.internal.DataSource();

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
        var key = v.getAttribute("key");
        ds.value(key, val);
    }
    return ds;
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

com.sweattrails.api.NullDataSource.prototype = new com.sweattrails.api.internal.DataSource();

/**
 * NullDataSourceBuilder -
 */

com.sweattrails.api.NullDataSourceBuilder = function() {
};

com.sweattrails.api.NullDataSourceBuilder.prototype.build = function(elem) {
    return new com.sweattrails.api.NullDataSource();
};

/**
 * ProxyDataSource -
 * 
 * @param {object} proxy Object to obtain/submit data from and to. The object 
 * should have <tt>getProxyData()</tt> and <tt>submutProxyData(object)</tt>
 * methods.
 */
com.sweattrails.api.ProxyDataSource = function(proxy) {
    this.view = [];
    this.proxy = proxy;
    this.data = null;
    this.reset();
    return this;
};

com.sweattrails.api.ProxyDataSource.prototype = new com.sweattrails.api.internal.DataSource();

com.sweattrails.api.ProxyDataSource.prototype.reset = function() {
    this.data = this.proxy.getProxyData();
    this.ix = 0;
    this.object = null;
};

com.sweattrails.api.ProxyDataSource.prototype.submit = function() {
    this.data = null;
    this.proxy.submitProxyData && this.proxy.submitProxyData(this.object);
};

/**
 * DataSourceBuilder -
 */

com.sweattrails.api.DataSourceBuilder = function() {
    this.jsonbuilder = new com.sweattrails.api.JSONDataSourceBuilder();
    this.staticbuilder = new com.sweattrails.api.StaticDataSourceBuilder();
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
    } else if (elem.getAttribute("source")) {
    	ret = this.custombuilder.build(elem);
    } else {
        var values = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "value");
        if (values.length > 0) {
            ret = this.staticbuilder.build(elem, values);
        } else {
            ret = (def_ds) ? def_ds : this.nullbuilder.build(elem);
        }
    }
    if (ret) {
        ret.debug = elem.getAttribute("debug");
    	if (elem.getAttribute("ondata")) {
            ret.onData = getfunc(elem.getAttribute("ondata"));
    	}
    	if (elem.getAttribute("nodata")) {
            ret.noData = getfunc(elem.getAttribute("nodata"));
    	}
    	if (elem.getAttribute("renderdata")) {
            ret.renderData = getfunc(elem.getAttribute("renderdata"));
    	}
    	if (elem.getAttribute("ondataend")) {
            ret.onDataEnd = getfunc(elem.getAttribute("ondataend"));
    	}
    	if (elem.getAttribute("onerror")) {
            ret.onDataError = getfunc(elem.getAttribute("ondataerror"));
    	}
    	if (elem.getAttribute("onsubmitted")) {
            ret.onDataSubmitted = getfunc(elem.getAttribute("onsubmitted"));
    	}
    }
    return ret;
};

com.sweattrails.api.dataSourceBuilder = new com.sweattrails.api.DataSourceBuilder();
