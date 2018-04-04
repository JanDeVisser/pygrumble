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

com.sweattrails.api.internal.RequestVariable = class {
    constructor(name, value) {
        this.name = name;
        this.value = value;
        this.type = "requestvariable";
    };

    stringValue() {
        let v = this.value;
        let f = null;
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

    stream() {
        $$.log(this, `stream ${this.stringValue()}`);
        this.owner.push(
`Content-Disposition: form-data; name="${this.name}"

${this.stringValue()}`);
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.FileRequestVariable = class extends com.sweattrails.api.internal.RequestVariable {
    constructor(name, file) {
        super(this, name, file);
        this.type = "filerequestvariable";
    };

    stringValue() {
        return this.value.name;
    };

    stream() {
        $$.log(this, "stream file " + this.value.name);
        const reader = new FileReader();
        if (!reader) {
            alert("Could not create FileReader");
            return false;
        }
        $$.log(this, `Created file reader for ${this.value.name}`);
        /* (custom properties:) */
        reader.segment = this.owner.push(this.name,
`; filename="${this.value.name}"
Content-Type: ${this.value.type}
`);
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
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.VariableFactories = {
    "File": com.sweattrails.api.internal.FileRequestVariable
};

com.sweattrails.api.internal.DefaultVariableFactory = com.sweattrails.api.internal.RequestVariable;

com.sweattrails.api.internal.makeVariable = function(name, value, type = typeof(value)) {
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

com.sweattrails.api.internal.HttpResponse = class {
    constructor(httpRequest) {
        this.type = "httpresponse";
        this.id = httpRequest.request.id;
        this.contenttype = httpRequest.getResponseHeader("Content-Type");
        this.request = httpRequest.request;
        this.httpRequest = httpRequest;
        this.data = this.httpRequest.responseText;
        this.status = httpRequest.status;
    }

    handle() {
        if (this.request.onHttpResponse) {
            this.request.onHttpResponse(this);
        }
        if (this.request.datasource && this.request.datasource.onHttpResponse) {
            this.request.datasource.onHttpResponse(this);
        }
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.JSONResponse = class extends com.sweattrails.api.internal.HttpResponse {
    constructor(httpRequest) {
        super(httpRequest);
        this.type = "jsonresponse";
        if (this.data) {
            try {
                $$.log(this, `Parsing JSON text ${this.data}`);
                this.object = JSON.parse(this.data);
            } catch (e) {
                $$.log(this, "Exception parsing JSON text");
                this.object = this.data;
                this.status = -1;
            }
        } else {
            this.object = {};
        }
    };

    handle() {
        if (this.request.datasource && this.request.datasource.onJSONData) {
            this.request.datasource.onJSONData(this.object);
        }
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.ResponseFactories = { };

com.sweattrails.api.internal.ResponseFactories[com.sweattrails.api.HttpContentType.json] = com.sweattrails.api.internal.JSONResponse;

com.sweattrails.api.getResponse = function(contenttype, httpRequest) {
    $$.log(this, `getResponse(${contenttype})`);
    const factory = com.sweattrails.api.internal.ResponseFactories[contenttype];
    if (!factory) {
        factory = com.sweattrails.api.internal.HttpResponse;
    }
    return new factory(httpRequest);
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.getHttpRequest = function(request) {
    const httpRequest = new XMLHttpRequest();
    if (!httpRequest) {
        alert('Cannot create an XMLHTTP instance');
        return false;
    }

    if (!httpRequest.sendAsBinary) {
        httpRequest.sendAsBinary = (data) => {
            const len = data.length;
            const ui8Data = new Uint8Array(len);
            for (let ix = 0; ix < len; ix++) {
                ui8Data[ix] = data.charCodeAt(ix) & 0xff;
            }
            this.send(ui8Data);
        }
    }

    httpRequest.request = request;
    httpRequest.onreadystatechange = function() {
        if (this.readyState === 4) {
            this.request.log(`Received response. Status ${this.status}`);
            const object = [];
            if ((this.status >= 200 && this.status <= 200) || this.status === 304) {
                const redir = this.getResponseHeader("ST-JSON-Redirect");
                if (redir && this.request.onRedirect) {
                    this.request.onRedirect(object, redir);
                } else {
                    const contenttype = this.getResponseHeader("Content-Type")
                                            .split(";")[0];
                    const response = com.sweattrails.api.getResponse(contenttype, this);
                    response.handle();
                }
                this.request.onSuccess();
                if (this.request.onSubmitted) {
                    this.request.onSubmitted();
                }
                this.request.semaphore = 0;
                this.request.log("response processed");
            } else {
                this.request.log(`  *** XMLHttp Error *** ${this.status}`);
                if (this.request.onError) {
                    this.request.onError(this.status, this.responseText);
                } else {
                    alert(
`XMLHttpRequest for ${this.request.url} returned ${this.status}:
${this.responseText}`);
                }
                this.request.semaphore = this.status;
                this.request.log("Error processed");
            }
        }
    };
    return httpRequest;
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.HttpRequest = class {
    constructor(url, onSuccess = undefined, onError = undefined) {
        this.type = "httprequest";
        this.id = url;
        this.url = url;
        if (onSuccess) {
            this.onSuccess = onSuccess;
        }
        if (onError) {
            this.onError = onError;
        }
        this.variables = [];
        this.status = 0;
        this.semaphore = 0;
        return this;
    };

    add(name, value) {
        if (!name && !value) {
            $$.log(this, " --> All NULL");
            return this;
        } else if (value instanceof Array) {
            value.forEach((v) => {
                this.add(name, v);
            });
        } else if ((value instanceof Object) && !(value instanceof File)) {
            Object.entries(value).forEach(([n, v]) => {
                this.add(((name) ? (name + ".") : "") + n, v);
            });
        } else {
            const variable = com.sweattrails.api.internal.makeVariable(name, value);
            this.variables.push(variable);
            variable.owner = this;
            variable.request = this.request;
        }
        return this;
    };

    clear() {
    };

    execute() {
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
        const keyval = (typeof(key) !== 'undefined') ? key : '$$';
        this.processedUrl = this.url
                                .replace('$$', keyval)
                                .replace(/\$([\w.]+)/g, (match, submatch) => {
                                     return __.getvar(submatch);
                                 });
        this.clear();
        $$.log(this, "Submitting data to " + this.processedUrl);
        this.serialize();
    };

    onSuccess() {
        if (this.datasource && this.datasource.onSuccess) {
        	this.datasource.onSuccess();
        }
    };

    onSubmitted() {
        if (this.datasource && this.datasource.onSubmitted) {
        	this.datasource.onSubmitted();
        }
    };

    onRedirect(object, redir) {
        if (this.datasource && this.datasource.onRedirected) {
        	this.datasource.onRedirected(object, redir);
        }
    };

    onError(code, object) {
        this.log(`HTTP Error ${code}`);
        this.post = false;
        if (this.datasource && this.datasource.onError) {
            this.log("Calling onError on datasource");
        	this.datasource.onError(code, object);
        }
    };

    log(...args) {
        args[0] = `XMLHttp - ${args[0]}`;
        args.unshift(this);
        this.datasource && $$.log(...args);
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.FormRequest = class extends com.sweattrails.api.internal.HttpRequest {
    constructor(url) {
        super(url);
        this.type = "formrequest";
    };

    serialize() {
        function e(s) {
            return encodeURIComponent(s).replace(/%20/g, "+");
        }
        const segments = [];
        this.variables.forEach((v) => {
            segments.push(`${e(v.name)}=${e(v.stringValue())}`);
        });
        const body = segments.join("\r\n");
        this.log(
`POST ${this.processedUrl} as form data with body
${body}`);
        this.httpRequest.open("POST", this.processedUrl, this.async);
        this.httpRequest.setRequestHeader("Content-Type", com.sweattrails.api.HttpContentType.form);
        this.httpRequest.send(body);
        return ret;
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.JSONRequest = class extends com.sweattrails.api.internal.HttpRequest {
    constructor(url) {
        super(url);
        this.type = "jsonrequest";
    };

    serialize() {
        const obj = {};
        this.variables.forEach((v) => {
            __.setvar(v.name, v.stringValue(), obj);
        });
        this.submit(JSON.stringify(obj));
    };

    submit(body) {
        const method = this.method || "POST";
        this.log(
`${method} ${this.processedUrl} as JSON data with body
${body}`);
        this.httpRequest.open(method, this.processedUrl, this.async);
        this.httpRequest.setRequestHeader("ST-JSON-Request", "true");
        this.httpRequest.send(body);
    };
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.GetRequest = class extends com.sweattrails.api.internal.JSONRequest {
    constructor(url) {
        super(url);
        this.type = "getrequest";
    };

    submit(body) {
        const method = this.method || "GET";
        this.log(method + " " + this.processedUrl);
        this.httpRequest.open(method, this.processedUrl, this.async);
        this.httpRequest.setRequestHeader("ST-JSON-Request", body);
        this.httpRequest.send(null);
    };

    onSubmitted() {
    };
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.UploadRequest = class extends com.sweattrails.api.internal.HttpRequest {
    constructor(url) {
        super(url);
        this.type = "uploadrequest";
        this.segments = [];
    };

    push(name, s) {
        s =
`Content-Disposition: form-data; name=${name}${s}
`;
        return this.segments.push(s) - 1;
    };

    append(index, s) {
        return this.segments[index] += s + "\r\n";
    };

    serialize() {
        this.segments = [];
        this.status = 1;
        $$.log(this, `Serializing ${this.variables.length} variables`);
        this.variables.forEach((v) => {
            v.stream();
        });
        this.submit();
    };

    submit() {
        $$.log(this, `UploadRequest.submit. status = ${this.status}`);
        this.status--;
        if (this.status == 0) {
            this.log(`POST ${this.processedUrl} as upload form`);
            this.httpRequest.open("POST", this.processedUrl, this.async);
            const boundary = "---------------------------" + Date.now().toString(16);
            this.httpRequest.setRequestHeader("Content-Type", `multipart/form-data; boundary=${boundary}`);
            this.httpRequest.sendAsBinary(
`--${boundary}
${this.segments.join(`--${boundary}
`)}--${boundary}--
`);
        }
    };

    clear() {
        this.segments = [];
    };
}

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
