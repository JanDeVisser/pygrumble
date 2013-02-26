com.sweattrails.api.JSONRequest = function(url) {
    this.url = url
    if (arguments.length > 1) {
        this.onSuccess = arguments[1]
    }
    if (arguments.length > 2) {
        this.onError = arguments[2]
    }
    this.params = {}
    return this
}

com.sweattrails.api.JSONRequest.prototype.parameter = function(param, value) {
    this.params[param] = value
}

com.sweattrails.api.getHttpRequest = function(jsonRequest) {
    var httpRequest = getXmlHttpRequest()
    if (!httpRequest) {
        return false;
    }

    httpRequest.request = jsonRequest
    httpRequest.onreadystatechange = function() {
        if (this.readyState == 4) {
            if ((this.status >= 200 && this.status <= 200) || this.status == 304) {
                if (this.responseText != "") {
                    var object = JSON.parse(this.responseText)
                    var posted = this.request.post
                    this.request.post = false
                    this.request.object = null
                    this.request.params = []
                    this.request.onSuccess(object)
                    if (posted && this.request.onSubmitted) {
                        this.request.onSubmitted()
                    }
                    this.request.semaphore = 0
                }
            } else {
                if (this.request.onError != null) {
                    this.request.onError(this.status)
                } else {
                    alert("XMLHttpRequest for " + this.request.url + " returned " + this.status)
                }
                this.request.semaphore = this.status
            }
        }
    }
    return httpRequest
}

com.sweattrails.api.JSONRequest.prototype.execute = function() {
    var httpRequest = com.sweattrails.api.getHttpRequest(this)
    if (!httpRequest) {
        return false;
    }

    this.semaphore = 1
    if (this.async == null) this.async = true
    if (this.post == null) this.post = false
    if (!this.body) {
        var parameters = new FormData()
        for (p in this.params) {
            parameters.append(p, this.params[p])
        }
        console.log(((this.post) ? "POST " : "GET " ) + this.url)
        httpRequest.open((this.post) ? "POST" : "GET", this.url, this.async);
        httpRequest.send(parameters)
    } else {
        console.log(((this.post) ? "POST " : "GET " ) + this.url)
        httpRequest.open((this.post) ? "POST" : "GET", this.url, this.async);
        httpRequest.send(this.body)
    }
    return true
}

com.sweattrails.api.JSONRequest.prototype.onSuccess = function(data) {
    this.data = data
    if (this.datasource && this.datasource.onJSONData) {
	this.datasource.onJSONData(data)
    }
}

com.sweattrails.api.JSONRequest.prototype.onSubmitted = function() {
    if (this.datasource && this.datasource.onSubmitted) {
	this.datasource.onSubmitted()
    }
}

com.sweattrails.api.JSONRequest.prototype.onError = function(code) {
    this.post = false
    if (this.datasource && this.datasource.onError) {
	this.datasource.onError(code)
    }
}

/**
 * DataSource -
 */

com.sweattrails.api.internal.DataSource = function() {
    this.submitparams = {}
}

com.sweattrails.api.internal.DataSource.prototype.addView = function(v) {
    if (!this.view) {
	this.view = []
    }
    this.view.push(v)
}

com.sweattrails.api.internal.DataSource.prototype.submitParameter = function(p, v) {
    this.submitparams[p] = v
}

com.sweattrails.api.internal.DataSource.prototype.processData = function() {
    if (!this.view) {
	this.view = []
    }
    this.runCallbacks("onData", [this.data])
    if ((this.data == null) || (Array.isArray(this.data) && (this.data.length == 0))) {
        this.runCallbacks("noData", [])
    } else {
        for(var n = this.next(); n != null; n = this.next()) {
            this.runCallbacks("renderData", [n])
        }
    }
    this.runCallbacks("onDataEnd", [this.data])
}

com.sweattrails.api.internal.DataSource.prototype.next = function() {
    if (this.data == null) {
        return null
    } else {
	if (Array.isArray(this.data)) {
	    if (this.ix < this.data.length) {
		return this.data[this.ix++]
	    } else {
		return null
	    }
	} else {
	    this.object = (this.object == null) ? this.data : null
	    return this.object
	}
    }
}

com.sweattrails.api.internal.DataSource.prototype.reset = function() {
    if (arguments.length > 0) {
        this.data = arguments[0]
    }
    this.ix = 0
    this.object = null
}

com.sweattrails.api.internal.DataSource.prototype.execute = function() {
    this.reset()
    this.processData()
}

com.sweattrails.api.internal.DataSource.prototype.getObject = function() {
    return this.object
}

com.sweattrails.api.internal.DataSource.prototype.setObject = function(obj) {
    this.object = obj || {}
}

com.sweattrails.api.internal.DataSource.prototype.createObjectFrom = function(context) {
    this.object = null
    if (this.factory) {
        this.object = this.factory(context)
    } else {
        this.object = {}
        for (p in this.submitparams) {
            var v = this.submitparams[p]
            if (typeof(v) === "function") {
                this.object[p] = v(context)
            } else if (v.indexOf("()") == (v.length() - 2)) {
                func = v.substring(0, v.length() - 2)
                f = getfunc(func)
                if (f) {
                    this.object[p] = f(context)
                }
            } else if (v.indexOf("$") == 0) {
                this.object[p] = context[v.substr(1)]
            } else {
                this.object[p] = v
            }
        }
    }
    return this.object
}

com.sweattrails.api.internal.DataSource.prototype.submit = function() {
}

com.sweattrails.api.internal.DataSource.prototype.runCallbacks = function(cb, args) {
    this[cb] && this[cb].apply(this, args)
    for (var vix in this.view) {
        var v = this.view[vix]
        v[cb] && v[cb].apply(v, args)
    }
}

com.sweattrails.api.internal.DataSource.prototype.onSubmitted = function() {
    this.runCallbacks("onDataSubmitted", [])
}

com.sweattrails.api.internal.DataSource.prototype.onError = function(errorinfo) {
    this.runCallbacks("onDataError", [errorinfo])
}

/**
 * JSONDataSource -
 */

com.sweattrails.api.JSONDataSource = function(url) {
    this.reset(null)
    this.request = new com.sweattrails.api.JSONRequest(url)
    this.request.datasource = this
    this.submitAsJSON = true
    return this
}

com.sweattrails.api.JSONDataSource.prototype = new com.sweattrails.api.internal.DataSource()

com.sweattrails.api.JSONDataSource.prototype.parameter = function(param, value) {
    this.request.parameter(param, value)
}

com.sweattrails.api.JSONDataSource.prototype.onJSONData = function(data) {
    this.reset(data)
    this.processData()
}

com.sweattrails.api.JSONDataSource.prototype.execute = function() {
    this.data = null
    this.request.execute()
}

com.sweattrails.api.JSONDataSource.prototype.addObject = function(obj, prefix) {
    prefix = prefix || ""
    for (var p in obj) {
        var v = obj[p]
        if (typeof(v) == "object") {
            this.addObject(prefix + p + ".", v)
        } else if (typeof(v) == "function") {
            continue
        } else {
            console.log("--" + prefix + p + "=" + v)
            this.parameter(prefix + p, v)
        }
    }
}

com.sweattrails.api.JSONDataSource.prototype.setParameters = function() {
    if (this.submitAsJSON) {
        this.request.body = JSON.stringify(this.object)
    } else {
        this.addObject(this.object)
    }
}


com.sweattrails.api.JSONDataSource.prototype.submit = function() {
    this.data = null
    this.request.post = true
    this.setParameters()
    this.request.execute()
}

/**
 * JSONDataSourceBuilder -
 */

com.sweattrails.api.JSONDataSourceBuilder = function() {
}

com.sweattrails.api.JSONDataSourceBuilder.prototype.build = function(elem) {
    var ds = new com.sweattrails.api.JSONDataSource(elem.getAttribute("url"))
    this.submitAsJSON = true
    if (elem.getAttribute("submit")) {
        this.submitAsJSON = elem.getAttribute("submit") == "json"
    }
    var params = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "parameter")
    for (var ix = 0; ix < params.length; ix++) {
	var p = params[ix]
	ds.parameter(p.getAttribute("name"), p.getAttribute("value"))
    }
    params = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "submitparameter")
    for (ix = 0; ix < params.length; ix++) {
	p = params[ix]
	ds.submitParameter(p.getAttribute("name"), p.getAttribute("value"))
    }
    return ds
}

/**
 * CustomDataSource -
 */

com.sweattrails.api.CustomDataSource = function(func, submitfnc) {
    this.data = null
    this.view = []
    this.func = (typeof(func) == 'function') ? func : getfunc(func)
    if (submitfnc) {
	this.submitfnc = (typeof(submitfnc) == 'function') ? submitfnc : getfunc(submitfnc)
    }
    this.reset()
    return this
}

com.sweattrails.api.CustomDataSource.prototype = new com.sweattrails.api.internal.DataSource()

com.sweattrails.api.CustomDataSource.prototype.reset = function() {
    this.data = this.func()
    for (var ix = 0; ix < this.data.length; ix++) {
        console.log(ix + ": " + this.data[ix].key + ", " + this.data[ix].value)
    }
    this.ix = 0
    this.object = null
}

com.sweattrails.api.CustomDataSource.prototype.submit = function() {
    this.data = null
    if (this.submitfnc) {
	this.submitfnc(this.object)
    }
}

/**
 * CustomDataSourceBuilder -
 */

com.sweattrails.api.CustomDataSourceBuilder = function() {
}

com.sweattrails.api.CustomDataSourceBuilder.prototype.build = function(elem) {
    var ds = null
    if (elem.getAttribute("source")) {
	ds = new com.sweattrails.api.CustomDataSource(elem.getAttribute("source"), elem.getAttribute("submit"))
    }
    return ds
}

/**
 * StaticDataSource -
 */

com.sweattrails.api.StaticDataSource = function() {
    this.reset(null)
    this.data = []
    this.view = []
    return this
}

com.sweattrails.api.StaticDataSource.prototype = new com.sweattrails.api.internal.DataSource()

com.sweattrails.api.StaticDataSource.prototype.value = function(key, value) {
    this.data.push({ key: key, value: value })
}

/**
 * StaticDataSourceBuilder -
 */

com.sweattrails.api.StaticDataSourceBuilder = function() {
}

com.sweattrails.api.StaticDataSourceBuilder.prototype.build = function(elem) {
    var ds = new com.sweattrails.api.StaticDataSource()
    var values = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "value")
    for (var ix = 0; ix < values.length; ix++) {
	var v = values[ix]
	var val = v.getAttribute("text")
	var key = v.getAttribute("key")
	ds.value(key, val)
    }
    return ds
}

/**
 * ProxyDataSource -
 */

com.sweattrails.api.ProxyDataSource = function(proxy) {
    this.view = []
    this.proxy = proxy
    this.data = null
    this.reset()
    return this
}

com.sweattrails.api.ProxyDataSource.prototype = new com.sweattrails.api.internal.DataSource()

com.sweattrails.api.ProxyDataSource.prototype.reset = function() {
    this.data = this.proxy.getProxyData()
    this.ix = 0
    this.object = null
}

com.sweattrails.api.ProxyDataSource.prototype.submit = function() {
    this.data = null
    this.proxy.submitProxyData && this.proxy.submitProxyData(this.object)
}

/**
 * DataSourceBuilder -
 */

com.sweattrails.api.DataSourceBuilder = function() {
    this.jsonbuilder = new com.sweattrails.api.JSONDataSourceBuilder()
    this.staticbuilder = new com.sweattrails.api.StaticDataSourceBuilder()
    this.custombuilder = new com.sweattrails.api.CustomDataSourceBuilder()
    return this
}

com.sweattrails.api.DataSourceBuilder.prototype.build = function(elem) {
    var ret = null
    var datasources = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "datasource")
    if (datasources && (datasources.length > 0)) {
	elem = datasources[0]
    }
    if (elem.getAttribute("url")) {
	ret = this.jsonbuilder.build(elem)
    } else if (elem.getAttribute("source")) {
	ret = this.custombuilder.build(elem)
    } else {
	ret = this.staticbuilder.build(elem)
    }
    if (ret != null) {
	if (elem.getAttribute("ondata")) {
	    ret.onData = getfunc(elem.getAttribute("ondata"))
	}
	if (elem.getAttribute("nodata")) {
	    ret.noData = getfunc(elem.getAttribute("nodata"))
	}
	if (elem.getAttribute("renderdata")) {
	    ret.renderData = getfunc(elem.getAttribute("renderdata"))
	}
	if (elem.getAttribute("ondataend")) {
	    ret.onDataEnd = getfunc(elem.getAttribute("ondataend"))
	}
    }
    return ret
}

com.sweattrails.api.dataSourceBuilder = new com.sweattrails.api.DataSourceBuilder()

