/*
 * Copyright (c) 2017 Jan de Visser (jan@sweattrails.com)
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

com.sweattrails.api.HttpContentType = {
    plain:  "text/plain",
    json:   "text/json",
    html:   "text/html",
    form:   "application/x-www-form-urlencoded",
    upload: "multipart/form-data"
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.RequestVariable = function(name, value) {
    this.name = name;
    this.value = value;
    this.type = "requestvariable";
};

com.sweattrails.api.internal.RequestVariable.prototype.stringValue = function() {
    var v = this.value;
    var f = null;
    if (typeof(v) === "function") {
        f = v;
    } else if (v && v.endsWith && v.endsWith("()")) {
        f = __.getfunc(v.substring(0, v.length() - 2));
    }
    if (f) {
        v = f();
    } else if (v && v.indexOf && (v.indexOf("$") === 0)) {
        v = __.getvar(v.substr(1));
    }
    return v;
};

com.sweattrails.api.internal.RequestVariable.prototype.stream = function() {
    $$.log(this, "stream " + this.stringValue());
    this.owner.push("Content-Disposition: form-data; name=\"" + this.name + "\"\r\n\r\n" + this.stringValue());
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.FileRequestVariable = function(name, file) {
    com.sweattrails.api.internal.RequestVariable.call(this, name, file);
    this.type = "filerequestvariable";
};

com.sweattrails.api.internal.FileRequestVariable.prototype = new com.sweattrails.api.internal.RequestVariable();

com.sweattrails.api.internal.FileRequestVariable.prototype.stringValue = function() {
    return this.value.name;
};

com.sweattrails.api.internal.FileRequestVariable.prototype.stream = function() {
    $$.log(this, "stream file " + this.value.name);
    var reader = new FileReader();
    if (!reader) {
        alert("Could not create FileReader");
        return false;
    }
    $$.log(this, "Created file reader for " + this.value.name);
    /* (custom properties:) */
    reader.segment = this.owner.push(this.name, "; filename=\""+ this.value.name +
        "\"\r\nContent-Type: " + this.value.type + "\r\n");
    reader.owner = this.owner;
    /* (end of custom properties) */
    reader.onload = function(ev) {
        console.log("Read file. Updating segment " + ev.target.segment);
        ev.target.owner.append(ev.target.segment, ev.target.result);
        ev.target.owner.submit();
    };
    this.owner.status++;
    reader.readAsBinaryString(this.value);
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.VariableFactories = {
    "File": com.sweattrails.api.internal.FileRequestVariable
};

com.sweattrails.api.internal.DefaultVariableFactory = com.sweattrails.api.internal.RequestVariable;

com.sweattrails.api.internal.makeVariable = function(name, value) {
    var type = (arguments.length > 2) ? arguments[2] : typeof(value);
    if (value instanceof File) {
        type = "File"
    } else if (value instanceof Object) {
        type = "Object";
    }
    var factory = com.sweattrails.api.internal.VariableFactories[type];
    if (!factory) {
        factory = com.sweattrails.api.internal.DefaultVariableFactory;
    }
    return new factory(name, value);
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.HttpResponse = function(httpRequest) {
    if (httpRequest) {
        this.type = "httpresponse";
        this.id = httpRequest.request.id;
        this.contenttype = httpRequest.getResponseHeader("Content-Type");
        this.request = httpRequest.request;
        this.httpRequest = httpRequest;
        this.data = this.httpRequest.responseText;
        this.status = httpRequest.status;
    }
};

com.sweattrails.api.internal.HttpResponse.prototype.handle = function() {
    if (this.request.onHttpResponse) {
        this.request.onHttpResponse(this);
    }
    if (this.request.datasource && this.request.datasource.onHttpResponse) {
        this.request.datasource.onHttpResponse(this);
    }
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.JSONResponse = function(httpRequest) {
    com.sweattrails.api.internal.HttpResponse.call(this, httpRequest);
    this.type = "jsonresponse";
    if (this.data) {
        try {
            this.object = JSON.parse(this.data);
        } catch (e) {
            console.log("Exception parsing JSON text " + this.responseText);
            this.object = this.responseText;
            this.status = -1;
        }
    }
};

com.sweattrails.api.internal.JSONResponse.prototype = new com.sweattrails.api.internal.HttpResponse();

com.sweattrails.api.internal.JSONResponse.prototype.handle = function() {
    if (this.request.datasource && this.request.datasource.onJSONData) {
        this.request.datasource.onJSONData(this.object);
    }
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.ResponseFactories = { };

com.sweattrails.api.internal.ResponseFactories[com.sweattrails.api.HttpContentType.json] = com.sweattrails.api.internal.JSONResponse;

com.sweattrails.api.getResponse = function(contenttype, httpRequest) {
    $$.log(this, "getResponse(" + contenttype + ")");
    var factory = com.sweattrails.api.internal.ResponseFactories[contenttype];
    if (!factory) {
        factory = com.sweattrails.api.internal.HttpResponse;
    }
    return new factory(httpRequest);
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.getHttpRequest = function(request) {
    var httpRequest;

    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        httpRequest = new XMLHttpRequest();
    } else if (window.ActiveXObject) { // IE
        try {
            httpRequest = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try {
                httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (e) {}
        }
    }

    if (!httpRequest) {
        alert('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    
    if (!httpRequest.sendAsBinary) {
        httpRequest.sendAsBinary = function(sData) {
            var nBytes = sData.length, ui8Data = new Uint8Array(nBytes);
            for (var nIdx = 0; nIdx < nBytes; nIdx++) {
                ui8Data[nIdx] = sData.charCodeAt(nIdx) & 0xff;
            }
            this.send(ui8Data);
        };
    }
    
    httpRequest.request = request;
    httpRequest.onreadystatechange = function() {
        if (this.readyState === 4) {
            this.request.log("Received response. Status " + this.status);
            var object = [];
            if ((this.status >= 200 && this.status <= 200) || this.status === 304) {
                var redir = this.getResponseHeader("ST-JSON-Redirect");
                if (redir && this.request.onRedirect) {
                    this.request.onRedirect(object, redir);
                } else {
                    var contenttype = this.getResponseHeader("Content-Type");
                    contenttype = contenttype.split(";")[0];
                    var response = com.sweattrails.api.getResponse(contenttype, this);
                    response.handle();
                }
                this.request.onSuccess();
                if (this.request.onSubmitted) {
                    this.request.onSubmitted();
                }
                this.request.semaphore = 0;
                this.request.log("response processed");
            } else {
                this.request.log("  *** XMLHttp Error *** " + this.status);
                if (this.request.onError) {
                    this.request.onError(this.status, this.responseText);
                } else {
                    alert("XMLHttpRequest for " + this.request.url + " returned " + this.status + ":\n" +
                        this.responseText);
                }
                this.request.semaphore = this.status;
                this.request.log("Error processed");
            }
        }
    };
    return httpRequest;
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.HttpRequest = function(url) {
    this.type = "httprequest";
    this.id = url;
    this.url = url;
    if (arguments.length > 1) {
        this.onSuccess = arguments[1];
    }
    if (arguments.length > 2) {
        this.onError = arguments[2];
    }
    this.variables = [];
    this.status = 0;
    this.semaphore = 0;
    return this;
};

com.sweattrails.api.internal.HttpRequest.prototype.add = function(name, value) {
    if (value instanceof Array) {
        value.forEach(function (v) {
            this.add(name, v);
        }, this);
    } else if ((value instanceof Object) && !(value instanceof File)) {
        for (var a in value) {
            if (!value.hasOwnProperty(a)) {
                continue;
            }
            this.add(((name) ? (name + ".") : "") + a, value[a]);
        }
    } else {
        var variable = com.sweattrails.api.internal.makeVariable(name, value);
        this.variables.push(variable);
        variable.owner = this;
        variable.request = this.request;
    }
};

com.sweattrails.api.internal.HttpRequest.prototype.clear = function() {
};

com.sweattrails.api.internal.HttpRequest.prototype.execute = function() {
    $$.log(this, "execute");
    this.httpRequest = com.sweattrails.api.getHttpRequest(this);

    if (!this.httpRequest) {
        $$.log(this, "Could not create XMLHttpRequest :-/");
        return false;
    }

    this.semaphore = 1;
    if (this.datasource && ("async" in this.datasource)) {
        this.async = this.datasource.async;
    }
    if (!("async" in this)) this.async = true;
    this.processedUrl = this.url;
    if (typeof(key) !== "undefined") {
        this.processedUrl = this.processedUrl.replace('$$', key);
    }
    this.processedUrl = this.processedUrl.replace(/\$([\w]+)/g, function() {
        return __.getvar(arguments[1]);
    });
    this.clear();
    $$.log(this, "Submitting data to " + this.processedUrl);
    this.serialize();
};

com.sweattrails.api.internal.HttpRequest.prototype.onSuccess = function() {
    if (this.datasource && this.datasource.onSuccess) {
    	this.datasource.onSuccess();
    }
};

com.sweattrails.api.internal.HttpRequest.prototype.onSubmitted = function() {
    if (this.datasource && this.datasource.onSubmitted) {
    	this.datasource.onSubmitted();
    }
};

com.sweattrails.api.internal.HttpRequest.prototype.onRedirect = function(object, redir) {
    if (this.datasource && this.datasource.onRedirected) {
    	this.datasource.onRedirected(object, redir);
    }
};

com.sweattrails.api.internal.HttpRequest.prototype.onError = function(code, object) {
    this.log("HTTP Error " + code);
    this.post = false;
    if (this.datasource && this.datasource.onError) {
        this.log("Calling onError on datasource");
    	this.datasource.onError(code, object);
    }
};

com.sweattrails.api.internal.HttpRequest.prototype.log = function(msg) {
    this.datasource && $$.log(this.datasource, "XMLHttp - " + msg);
};


/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.FormRequest = function(url) {
    com.sweattrails.api.internal.HttpRequest.call(this, url);
    this.type = "formrequest";
};

com.sweattrails.api.internal.FormRequest.prototype = new com.sweattrails.api.internal.HttpRequest();

com.sweattrails.api.internal.FormRequest.prototype.serialize = function() {
    function e(s) {
        return encodeURIComponent(s).replace(/%20/g, "+");
    }
    var segments = [];
    this.variables.forEach(function(v) {
        segments.push(e(v.name) + "=" + e(v.stringValue()));
    });
    var body = segments.join("\r\n");
    this.log("POST " + this.processedUrl + " as form data with body\n" + body);
    this.httpRequest.open("POST", this.processedUrl, this.async);
    this.httpRequest.setRequestHeader("Content-Type", com.sweattrails.api.HttpContentType.form);
    this.httpRequest.send(body);
    return ret;
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.JSONRequest = function(url) {
    com.sweattrails.api.internal.HttpRequest.call(this, url);
    this.type = "jsonrequest";
};

com.sweattrails.api.internal.JSONRequest.prototype = new com.sweattrails.api.internal.HttpRequest();

com.sweattrails.api.internal.JSONRequest.prototype.serialize = function() {
    var obj = {};
    this.variables.forEach(function (v) {
        __.setvar(v.name, v.stringValue(), obj);
    });
    this.submit(JSON.stringify(obj));
};

com.sweattrails.api.internal.JSONRequest.prototype.submit = function(body) {
    this.log("POST " + this.processedUrl + " as JSON data with body\n" + body);
    this.httpRequest.open("POST", this.processedUrl, this.async);
    this.httpRequest.setRequestHeader("ST-JSON-Request", "true");
    this.httpRequest.send(body);
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.GetRequest = function(url) {
    com.sweattrails.api.internal.JSONRequest.call(this, url);
    this.type = "getrequest";
};

com.sweattrails.api.internal.GetRequest.prototype = new com.sweattrails.api.internal.JSONRequest();

com.sweattrails.api.internal.GetRequest.prototype.submit = function(body) {
    this.log("GET " + this.processedUrl);
    this.httpRequest.open("GET", this.processedUrl, this.async);
    this.httpRequest.setRequestHeader("ST-JSON-Request", body);
    this.httpRequest.send(null);
};

com.sweattrails.api.internal.GetRequest.prototype.onSubmitted = null;

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.UploadRequest = function(url) {
    com.sweattrails.api.internal.HttpRequest.call(this, url);
    this.type = "uploadrequest";
    this.segments = [];
};

com.sweattrails.api.internal.UploadRequest.prototype = new com.sweattrails.api.internal.HttpRequest();

com.sweattrails.api.internal.UploadRequest.prototype.push = function(name, s) {
    s = "Content-Disposition: form-data; name=\"" + name + "\"" + s + "\r\n";
    return this.segments.push(s) - 1;
};

com.sweattrails.api.internal.UploadRequest.prototype.append = function(index, s) {
    return this.segments[index] += s + "\r\n";
};

com.sweattrails.api.internal.UploadRequest.prototype.serialize = function() {
    this.segments = [];
    this.status = 1;
    $$.log(this, "Serializing " + this.variables.length + " variables");
    this.variables.forEach(function (v) {
        v.stream();
    });
    this.submit();
};

com.sweattrails.api.internal.UploadRequest.prototype.submit = function() {
    $$.log(this, "UploadRequest.submit. status = " + this.status);
    this.status--;
    if (this.status == 0) {
        this.log("POST " + this.processedUrl + " as upload form");
        this.httpRequest.open("POST", this.processedUrl, this.async);
        var boundary = "---------------------------" + Date.now().toString(16);
        this.httpRequest.setRequestHeader("Content-Type", "multipart\/form-data; boundary=" + boundary);
        this.httpRequest.sendAsBinary("--" + boundary + "\r\n" +
            this.segments.join("--" + boundary + "\r\n") + "--" + boundary + "--\r\n");
    }
};

com.sweattrails.api.internal.UploadRequest.prototype.clear = function() {
    this.segments = [];
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.RequestFactories = { };

com.sweattrails.api.internal.RequestFactories[com.sweattrails.api.HttpContentType.plain] = com.sweattrails.api.internal.GetRequest;
com.sweattrails.api.internal.RequestFactories[com.sweattrails.api.HttpContentType.json] = com.sweattrails.api.internal.JSONRequest;
com.sweattrails.api.internal.RequestFactories[com.sweattrails.api.HttpContentType.form] = com.sweattrails.api.internal.FormRequest;
com.sweattrails.api.internal.RequestFactories[com.sweattrails.api.HttpContentType.upload] = com.sweattrails.api.internal.UploadRequest;

com.sweattrails.api.getRequest = function(contenttype, url) {
    var factory = com.sweattrails.api.internal.RequestFactories[contenttype];
    if (!factory) {
        factory = com.sweattrails.api.internal.GetRequest;
    }
    return new factory(url);
};

/* ----------------------------------------------------------------------- */

