/**
 * Column -
 */

com.sweattrails.api.tables = {};
com.sweattrails.api.format = {};
com.sweattrails.api.internal.format = {};
com.sweattrails.api.internal.build = {};
com.sweattrails.api.internal.format.integer = function(value) { return new Number(value).toFixed(0); };
com.sweattrails.api.internal.format.float = function(value, col) {
    var digits = col.digits;
    return (digits) ? new Number(value).toFixed(digits) : String.valueOf(value);
};
com.sweattrails.api.internal.format.time = function(value) { return prettytime(seconds_to_time(value)); };
com.sweattrails.api.internal.format.date = format_date;
com.sweattrails.api.internal.format.datetime = format_datetime;

com.sweattrails.api.internal.build.icon = function(col, elem) {
    col.align = "center";
    col.icons = {};
    var icons = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "icon");
    for (var ix = 0; ix < icons.length; ix++) {
	    var i = icons[ix];
	    col.icons[i.getAttribute("value")] = i.getAttribute("icon");
    }
};

com.sweattrails.api.internal.format.icon = function(value, col) {
    var url;
    if (col.url) {
        // Replace occurences of $$ with column value:
        url = col.url.replace('$$', value);
        // Replace occurrences of $<attribute> with <attribute> value:
        url = url.replace(/\$([\w]+)/g, function() {
            return object[arguments[1]];
        });
    } else if (value in col.icons) {
        url = col.icons[value];
    } else {
        url = value;
    }
    // If the URL is not fully qualified assume it refers to a .png in /image:
    if (!url.match(/^(\/.+)|(https?:\/\/.+)/)) {
        url = "/image/" + url + ".png";
    }
    var ret = new com.sweattrails.api.Image(url);
    ret.height = col.imgheight || col.size || "24";
    ret.width = col.imgwidth || col.size || "24";
    return ret;
};

com.sweattrails.api.internal.build.link = function(col, elem) {
    col.parameters = {};
    var params = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "parameter");
    for (var ix = 0; ix < params.length; ix++) {
	var p = params[ix];
        var n = p.getAttribute("name");
        if (!n || (n === "")) continue;
        var v = p.getAttribute("value");
        if (!v || (v === "")) {
            v = n;
        }
	    col.parameters[n] = v;
    }
};

com.sweattrails.api.internal.format.link = function(value, col, object) {
    url = col.url.replace('$$', value);
    url = url.replace(/\$([\w]+)/g, function() {
        return object[arguments[1]];
    });
    var ret = new com.sweattrails.api.Link(value, url);
    for (p in col.parameters) {
        ret.parameter(p, object[col.parameters[p]]);
    }
    return ret;
};

com.sweattrails.api.Column = function(table, label) {
    this.bridge = new com.sweattrails.api.internal.DataBridge();
    this.table = table;
    this.label = label;
    this.width = null;
    this.align = null;
    this.format = null;
    this.link = false;
    return this;
};

com.sweattrails.api.Column.prototype.setLink = function(url) {
    this.link = url;
};

com.sweattrails.api.Column.prototype.setProperty = function(prop) {
    this.bridge.get = prop;
};

com.sweattrails.api.Column.prototype.setFunction = function(func) {
    if (typeof(func) === "function") {
    	this.bridge.get = func;
    } else {
        this.bridge.get = __.getfunc(func) || new Function("data", func);
    }
};

com.sweattrails.api.Column.prototype.setWidth = function(width) {
    this.width = width;
};

com.sweattrails.api.Column.prototype.setFormat = function(elem) {
    var type = elem.getAttribute("type");
    this.format = com.sweattrails.api.internal.format[type] || com.sweattrails.api.format[type];
    var attrs = elem.attributes;
    for (var ix = 0; ix < attrs.length; ix++) {
        this[attrs[ix].name] = attrs[ix].value;
    }
    com.sweattrails.api.internal.build[type] && com.sweattrails.api.internal.build[type](this, elem);
};

com.sweattrails.api.Column.prototype.getValue = function(object) {
    var ret = this.bridge.getValue(object, this);
    if (ret && this.format) {
        ret = this.format(ret, this, object);
    }
    if (this.link) {
        if (this.table.form) {
            var f = function (object) {
                if (!this.form.ispopup) {
                    this.data = object;
                    this.form.popup();
                }
            };
            f = f.bind(this.table, object);
            ret = new com.sweattrails.api.Link(ret, f);
        } else {
            ret = new com.sweattrails.api.Link(ret, this.link.replace(/\$key/, object.key));
        }
    }
    return ret;
};

/*
 * Table -
 */
com.sweattrails.api.Table = function(container, id) {
    this.container = container;
    this.id = id;
    this.type = "table";
    com.sweattrails.api.STManager.register(this);
    this.table = null;
    if (arguments.length > 2) {
        this.setDataSource(arguments[2]);
    }
    this.columns = [];
    this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
    this.header = new com.sweattrails.api.ActionContainer(this, "header");
    return this;
};

com.sweattrails.api.Table.prototype.initForm = function(ds) {
    this.form = new com.sweattrails.api.Form("table-" + this.id, this.container, ds, true);
//        new com.sweattrails.api.ProxyDataSource(this), true)
};

com.sweattrails.api.Table.prototype.setDataSource = function(ds) {
    this.datasource = ds;
    ds.addView(this);
};

com.sweattrails.api.Table.prototype.addColumns = function() {
    for (var i = 0; i < arguments.length; i++) {
        this.columns.push(arguments[i]);
    }
};

com.sweattrails.api.Table.prototype.render = function() {
    $$.log(this, "render()");
    this.datasource.reset();
    this.datasource.execute();
};

com.sweattrails.api.Table.prototype.onData = function(data) {
    $$.log(this, "Table.onData");
    this.onrender && this.onrender(data);
    this.header.erase();
    this.footer.erase();
    if (this.table) {
        this.container.removeChild(this.table);
    }
    this.header.render();
    this.table = document.createElement("table");
    this.table.id = this.id + "-table";
    this.table.width = "100%";
    this.cellspacing = "0";
    this.container.appendChild(this.table);
    this.headerrow = document.createElement("tr");
    this.headerrow.id = this.id + "-header";
    this.headerrow.className = "tableheader";
    this.table.appendChild(this.headerrow);
    this.rowcolor = 'white';

    var th;
    if (this.counter) {
        th = document.createElement("th");
        th.innerHTML = "#";
        this.headerrow.appendChild(th);
    }
    for (var i = 0; i < this.columns.length; i++) {
        th = document.createElement("th");
        var coldef = this.columns[i];
        if (coldef.width) {
            th.width = coldef.width;
        }
        th.innerHTML = coldef.label;
        this.headerrow.appendChild(th);
    }
    this.count = 0;
};

com.sweattrails.api.Table.prototype.noData = function() {
    $$.log(this, "Table.noData");
    var emptyrow = document.createElement("tr");
    emptyrow.id = this.id + "-emptyrow";
    this.table.appendChild(emptyrow);
    var td = document.createElement("td");
    td.style.bgcolor = "white";
    td.colSpan = this.columns.length;
    td.innerHTML = "&#160;<i>No data</i>";
    emptyrow.appendChild(td);
};

com.sweattrails.api.Table.prototype.renderData = function(obj) {
    if (!obj) return;
    $$.log(this, "Table.renderData");
    var tr = document.createElement("tr");
    tr.style.backgroundColor = this.rowcolor;
    if (this.rowcolor === 'white') {
        this.rowcolor = 'lightblue';
    } else {
        this.rowcolor = 'white';
    }
    this.count++;
    var td;
    if (this.counter) {
        td = document.createElement("td");
        td.style.textAlign = "center";
        td.innerHTML = "" + this.count + ".";
        tr.appendChild(td);
    }
    for (var i = 0; i < this.columns.length; i++) {
        var coldef = this.columns[i];
        td = document.createElement("td");
        if (coldef.align) td.style.textAlign = coldef.align;
        var data = coldef.getValue(obj);
        if (!data) {
            if (typeof(obj.render) === 'function') {
                data = obj.render(i, coldef);
            }
        }
        if (data && (typeof(data) === "object") && data.render && (typeof(data.render) === "function")) {
            data = data.render();
        } else if (typeof(data) === 'boolean') {
            if (data) {
                var img = document.createElement("img");
                img.src = "/images/checkmark.png";
                img.height = "24px";
                img.width = "24px";
                data = img;
            } else {
                data = null;
            }
        }
        data = data || "&#160;";
        if ((typeof(data) === "string") || (typeof(data) === 'number')) {
            td.innerHTML = data;
        } else if (typeof(data) === "object") {
            td.appendChild(data);
        }
        tr.appendChild(td);
    }
    this.table.appendChild(tr);
};

com.sweattrails.api.Table.prototype.onDataEnd = function() {
    $$.log(this, "Table.onDataEnd");
    this.footer.render();
    this.onrendered && this.onrendered();
};

com.sweattrails.api.Table.prototype.openForm = function(object) {
    $$.log(this, "Table.openForm");
    if (this.form && !this.form.ispopup) {
        this.data = object;
        this.form.popup((!object) ? com.sweattrails.api.MODE_NEW : com.sweattrails.api.MODE_VIEW);
    }
    return true;
};

com.sweattrails.api.Table.prototype.reset = function(data) {
    $$.log(this, "Table.reset");
    this.datasource.reset(data);
    this.render();
};

com.sweattrails.api.Table.prototype.getProxyData = function() {
    return this.data;
};

com.sweattrails.api.Table.prototype.submitProxyData = function() {
    this.datasource.submit();
};

com.sweattrails.api.Table.prototype.pushProxyState = function(state) {
    this.datasource.pushState(state);
};

com.sweattrails.api.Table.prototype.popProxyState = function() {
    this.datasource.popState();
};

com.sweattrails.api.Table.prototype.onDataSubmitted = function() {
    $$.log(this, "Table.onDataSubmitted");
    this.form && this.form.ispopup && this.form.onDataSubmitted();
    this.onsubmitted && this.onsubmitted();
};

com.sweattrails.api.Table.prototype.onDataError = function(errorinfo) {
    $$.log(this, "Table.onDataError");
    this.form && this.form.ispopup && this.form.onDataError(errorinfo);
    this.onerror && this.onerror(errorinfo);
};

com.sweattrails.api.Table.prototype.populate = com.sweattrails.api.Table.prototype.render;

/**
 * TableBuilder -
 */

com.sweattrails.api.TableBuilder = function() {
    this.type = "builder";
    this.name = "tablebuilder";
    com.sweattrails.api.STManager.processor("table", this);
};

com.sweattrails.api.TableBuilder.prototype.process = function(t) {
    var p = t.parentNode;
    var name = t.getAttribute("name");
    console.log("tableBuilder: building " + name);
    var ds = com.sweattrails.api.dataSourceBuilder.build(t);
    var table = new com.sweattrails.api.Table(p, name, ds);
    table.onrender = t.getAttribute("onrender") && __.getfunc(t.getAttribute("onrender"));
    table.onrendered = t.getAttribute("onrendered") && __.getfunc(t.getAttribute("onrendered"));
    table.footer.build(t);
    var footer = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "footer");
    if (footer.length === 1) {
        table.footer.build(footer[0]);
    }
    var header = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "header");
    if (header.length === 1) {
        table.header.build(header[0]);
    }
    var forms = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "dataform");
    if (forms.length === 1) {
        var formelem = forms[0];
        var form_ds = com.sweattrails.api.dataSourceBuilder.build(formelem,
            new com.sweattrails.api.ProxyDataSource(table));
        table.initForm(form_ds);
        _.formbuilder.buildForm(table.form, formelem);
    }
    table.counter = t.getAttribute("counter") != null;
    var columns = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "column");
    for (var j = 0; j < columns.length; j++) {
        var c = columns[j];
        var col = new com.sweattrails.api.Column(table, c.getAttribute("label"));
        if (c.getAttribute("property")) {
            col.setProperty(c.getAttribute("property"));
        } else {
            col.setFunction(c.getAttribute("get"));
        }
        if (c.getAttribute("select")) {
            col.setLink(c.getAttribute("select"));
        }
        col.setWidth(c.getAttribute("width"));
        col.setFormat(c);
        table.addColumns(col);
    }
};

new com.sweattrails.api.TableBuilder();

com.sweattrails.api.Image = function(url) {
    this.url = url;
    if (arguments.length > 1) {
        this.alttext = arguments[1];
    }
    return this;
};

com.sweattrails.api.Image.prototype.render = function() {
    var img = document.createElement("img");
    img.src = this.url;
    if (this.width) img.width = this.width;
    if (this.height) img.height = this.height;
    if (this.alttext) img.alt = this.alttext;
    return img;
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.Link = function(display, url) {
    this.display = display || "&#160;";
    this.url = url;
    this.parameters = {};
    $$.log(this, "new Link: display " + this.display + ", this.url: " + this.url);
    return this;
};

com.sweattrails.api.Link.prototype.parameter = function(param, value) {
    this.parameters[param] = value;
};

com.sweattrails.api.Link.prototype.render = function() {
    var a = document.createElement("a");
    if (typeof(this.url) === "function") {
        a.href = "#";
        a.onclick = this.url;
    } else {
        var params = "";
        for (var p in this.parameters) {
            if (!this.parameters.hasOwnProperty(p)) {
                continue;
            }
            if (params === "") {
                params = "?";
            } else {
                params += "&";
            }
            params += (encodeURIComponent(p) + "=" + encodeURIComponent(this.parameters[p]));
        }
        a.href = this.url + params;
    }
    //a.innerHTML = this.display
    com.sweattrails.api.renderObject(a, this.display);
    return a;
};


