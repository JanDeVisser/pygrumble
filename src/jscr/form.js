/**
 * Form -
 */

com.sweattrails.api.MODE_VIEW = "view";
com.sweattrails.api.MODE_EDIT = "edit";
com.sweattrails.api.MODE_NEW = "new";

com.sweattrails.api.show_form = function() {
    var formname = arguments[0];
    var mode = ((arguments.length > 1) && arguments[1]) ? arguments[1] : com.sweattrails.api.MODE_NEW;
    var form = $(formname);
    if (form && !form.ispopup) {
        form.popup(mode);
    }
};

st_show_form = com.sweattrails.api.show_form;

com.sweattrails.api.internal.buildErrors = function(obj, e) {
    if (!e) return;
    if (typeof(e) === "string") {
        var o = {};
        o.message = e;
        o.field = this;
        e = o;
    }
    obj.errors = obj.errors || [];
    if (Array.isArray(e)) {
    	e.forEach(ST_int.buildErrors);
    } else {
    	obj.errors.push(e);
    }
};

com.sweattrails.api.Form = function(id, container, ds, popup) {
    this.id = id;
    this.type = "form";
    if (container) {
        this.setContainer(container);
    }
    if (ds) {
        this.setDataSource(ds);
    }
    if (popup) {
        this.makePopup();
    }
    this.fields = [];
    this.$ = {};
    this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
    this.header = new com.sweattrails.api.ActionContainer(this, "header");
    this.mode = com.sweattrails.api.MODE_VIEW;
    com.sweattrails.api.STManager.register(this);
    return this;
};

com.sweattrails.api.Form.prototype.setContainer = function(c) {
    if (typeof(c) === "string") {
    	this.container = document.getElementById(this.id);
    } else {
    	this.container = c;
    }
    this.table = null;
};

com.sweattrails.api.Form.prototype.makePopup = function() {
    var container = document.createElement("div");
    container.id = this.id + "-popup";
    container.className = this.className || "popup";
    container.hidden = true;
    this.container.appendChild(container);
    this.container = container;
};

com.sweattrails.api.Form.prototype.makeModal = function() {
	var body = document.getElementsByTagName("body")[0];
    this.overlay = document.getElementById("overlay");
    if (!this.overlay) {
    	this.overlay = document.createElement("div");
        this.overlay.id = "overlay";
        this.overlay.className = "overlay";
        this.overlay.hidden = true;
        body.appendChild(this.overlay);
    }
    var container = document.createElement("div");
    container.id = this.id + "-modal";
    container.className = "modal";
    container.hidden = true;
    body.appendChild(container);
    this.container = container;
    this.modal = true;
};

com.sweattrails.api.Form.prototype.setTable = function(tableid) {
    this.id = tableid;
    this.table = document.getElementById(this.id);
    this.container = null;
};

com.sweattrails.api.Form.prototype.setDataSource = function(ds) {
    this.datasource = ds;
    ds.addView(this);
};

com.sweattrails.api.Form.prototype.addField = function(fld) {
    $$.log(this, "Adding field " + fld.id);
    this.fields.push(fld);
    fld.form = this;
    if (typeof(fld.id) !== "undefined") {
        this.$[fld.id] = fld;
    }
};

com.sweattrails.api.Form.prototype.addAction = function(action) {
    this.actions.add(action);
};

com.sweattrails.api.Form.field = function(fld) {
    return this.$[fld];
};

com.sweattrails.api.Form.prototype.newTR = function() {
    if (!this.table) {
        this.table = document.createElement("table");
        this.table.width = "100%";
        p = (this.form) ? this.form : this.container;
        p.appendChild(this.table);
    }
    var tr = document.createElement("tr");
    this.table.appendChild(tr);
    return tr;
};

com.sweattrails.api.Form.prototype.render = function() {
    $$.log(this, "render() class: " + this.container.className);
    if (!this.container || !this.container.hidden || (this.container.className === "tabpage")) {
        if ((arguments.length > 0) && arguments[0]) {
            this.mode = arguments[0];
        } else if (this.init_mode) {
            this.mode = this.init_mode;
            this.init_mode = null;
        } else {
            this.mode = com.sweattrails.api.MODE_VIEW;
        }
        var obj = null;
        if (this.mode !== com.sweattrails.api.MODE_NEW) {
            this.datasource.execute();
        } else {
            if (typeof(this.initialize) === "function") {
                obj = this.initialize();
            }
            this.datasource.setObject(obj);
            this.renderData(this.datasource.getObject());
        }
    }
};

com.sweattrails.api.Form.prototype.renderData = function(obj) {
    com.sweattrails.api.dump(obj, "Rendering form with data -");
    this.header.erase();
    this.footer.erase();
    if (this.renderedFields) {
        this.renderedFields.forEach(function(f) { f.erase(); });
    }
    this.renderedFields = [];
    if (this.form) {
    	this.container.removeChild(this.form);
    	this.form = null;
    	this.table = null;
    }
    if (this.table) {
        this.container.removeChild(this.table);
        this.table = null;
    }
    this.header.render();
    if (this.type === "form") {
        this.form = document.createElement("form");
        this.form.name = "form-" + this.id;
        this.form.method = this.method;
        this.form.action = this.action;
        this.container.appendChild(this.form);
    }
    this.fields.forEach(function(f) {
    	$$.log(this, "rendering field %s", f.id);
        if (f.render(this.mode, obj)) {
            this.renderedFields.push(f);
        }
    }, this);
    this.footer.render();
};

com.sweattrails.api.Form.prototype.applyData = function() {
    var obj;

    // FIXME: Why?
    // if (this.mode !== com.sweattrails.api.MODE_NEW) {
    //     this.datasource.reset();
    //     this.datasource.next();
    // }
    obj = this.datasource.getObject();
    this.renderedFields.forEach(function(f) {
        if (!f.readonly) {
            f.assignValueToObject(obj);
        }
    });
    if (typeof(this.prepare) === "function") {
        this.prepare(obj);
    }
};

com.sweattrails.api.Form.prototype.submit = function() {
    this.errors = [];
    if (this.validator) {
        ST_int.buildErrors(this, this.validator());
    }
    var form = this;
    this.renderedFields.forEach(function(f) {
        f.errors = f.validate();
        if (f.errors) form.errors = form.errors.concat(f.errors);
    });
    if (this.errors.length > 0) {
        this.render(this.mode);
    } else {
        this.applyData();
        this.progress(this.submitMessage);
        $$.log(this, "Submitting form...");
        if (this.form) {
            this.form.submit();
        } else {
            this.datasource.submit();
        }
    }
};

com.sweattrails.api.Form.prototype.progressOff = function() {
    this.footer.progressOff();
};

com.sweattrails.api.Form.prototype.progress = function(msg) {
    this.footer.progress(msg);
};

com.sweattrails.api.Form.prototype.error = function(msg) {
    this.footer.error && this.footer.error(msg);
};

com.sweattrails.api.Form.prototype.popup = function(mode) {
    if (this.modal) {
    	document.getElementById("overlay").hidden = false;
    }
    this.container.hidden = false;
    this.ispopup = true;
    this.render(mode);
};

com.sweattrails.api.Form.prototype.close = function() {
    try {
        this.progressOff();
        if (this.ispopup) {
            this.container.hidden = true;
            if (this.modal) {
                this.overlay.hidden = true;
            }
        } else {
            if (this.mode !== com.sweattrails.api.MODE_VIEW) {
                this.render(com.sweattrails.api.MODE_VIEW);
            }
        }
    } finally {
        this.ispopup = false;
    }
};

com.sweattrails.api.Form.prototype.onData = function(data) {
    this.renderData(data);
    this.header.onData && this.header.onData(data);
    this.footer.onData && this.footer.onData(data);
    this.ondata && this.ondata();
};

com.sweattrails.api.Form.prototype.onRequestSuccess = function() {
    this.header.onSuccess && this.header.onSuccess();
    this.footer.onSuccess && this.footer.onSuccess();
    this.onsuccess && this.onsuccess();
};

com.sweattrails.api.Form.prototype.onDataSubmitted = function() {
    this.close();
    this.header.onDataSubmitted && this.header.onDataSubmitted();
    this.footer.onDataSubmitted && this.footer.onDataSubmitted();
    this.onsubmitted && this.onsubmitted();
};

com.sweattrails.api.Form.prototype.onDataError = function(errorinfo) {
    this.header.onDataError && this.header.onDataError(errorinfo);
    this.footer.onDataError && this.footer.onDataError(errorinfo);
    var handled = false;
    if (this.onerror) {
    	handled = this.onerror(errorinfo);
    }
    if (!handled) this.error("Error saving: " + errorinfo);
};

com.sweattrails.api.Form.prototype.onDataEnd = function() {
    this.header.onDataEnd && this.header.onDataEnd();
    this.footer.onDataEnd && this.footer.onDataEnd();
    this.ondataend && this.ondataend();
};

com.sweattrails.api.Form.prototype.onRedirect = function(href) {
    this.header.onRedirect && this.header.onRedirect(href);
    this.footer.onRedirect && this.footer.onRedirect(href);
    this.onredirect && this.onredirect(href);
};

/**
 * FormBuilder -
 */

com.sweattrails.api.FormBuilder = function() {
    this.type = "builder";
    this.name = "formbuilder";
    com.sweattrails.api.STManager.processor("form", this);
};

com.sweattrails.api.FormBuilder.prototype.process = function(f) {
    var id = f.getAttribute("name");
    $$.log(this, "Found form " + id);
    var ds = com.sweattrails.api.dataSourceBuilder.build(f);
    var form = new com.sweattrails.api.Form(id, f.parentNode, ds);
    var kind = f.getAttribute("kind");
    if (kind) {
        this.buildFormForKind(form, kind, f);
    } else {
        this.buildForm(form, f);
    }
};

com.sweattrails.api.FormBuilder.prototype.buildFormForKind = function(form, kind, elem) {
    this.buildForm(form, elem);
    form.schemads = new com.sweattrails.api.JSONDataSource("/schema/" + kind);
    form.schemads.async = false;
    form.schemads.form = form;
    form.schemads.renderData = function(obj) {
        for (var ix in obj.properties) {
            var p = obj.properties[ix];
            var fld = new com.sweattrails.api.FormField(this.form, p.name);
            fld.build(getDOMElement(p));            
        }
    };
    form.schemads.execute();
};

com.sweattrails.api.FormBuilder.prototype.buildForm = function(form, elem) {
    form.type = 'json';
    if (elem.getAttribute("type")) {
        form.type = elem.getAttribute("type").toLowerCase();
        if (["json", "form"].indexOf(form.type) < 0) {
            console.log("Invalid form type " + form.type + " for form " + form.id);
            form.type = "json";
        }
        if (form.type === "form") {
            form.action = elem.getAttribute("action");
            if (!form.action) {
                console.log("Missing form action for form " + form.id);
                form.type = "json";
            }
            form.method = "POST";
            if (elem.getAttribute("method")) {
                form.method = elem.getAttribute("method");
            }
        }
    }
    form.layout = "table";
    if (elem.getAttribute("layout")) {
        form.layout = elem.getAttribute("layout")
    }
    if (elem.getAttribute("mode")) {
        form.init_mode = elem.getAttribute("mode");
    }
    if (elem.getAttribute("initialize")) {
        form.initialize = __.getfunc(elem.getAttribute("initialize"));
    }
    if (elem.getAttribute("ondata")) {
        form.ondata = __.getfunc(elem.getAttribute("ondata"));
    }
    if (elem.getAttribute("onsubmitted")) {
        form.onsubmitted = __.getfunc(elem.getAttribute("onsubmitted"));
    }
    if (elem.getAttribute("onsuccess")) {
        form.onsuccess = __.getfunc(elem.getAttribute("onsuccess"));
    }
    if (elem.getAttribute("validate")) {
        this.validator = __.getfunc(elem.getAttribute("validate"));
    }
    if (elem.getAttribute("onerror")) {
        form.onerror = __.getfunc(elem.getAttribute("onerror"));
    }
    if (elem.getAttribute("onredirect")) {
        form.onredirect = __.getfunc(elem.getAttribute("onredirect"));
    }
    if (elem.getAttribute("class")) {
    	form.className = elem.getAttribute("class");
    }
    form.submitMessage = (elem.getAttribute("submitmessage")) ? elem.getAttribute("submitmessage") : "Saving ...";
    if (elem.getAttribute("popup") && ("true" === elem.getAttribute("popup"))) {
        form.makePopup();
    } else if (elem.getAttribute("modal") && ("true" === elem.getAttribute("modal"))) {
        form.makeModal();
    }
    this.copyNode(form, elem, elem.parentElement);
    form.fields.forEach(function (f) { f.postprocess();});
};

com.sweattrails.api.FormBuilder.prototype.copyNode = function(form, elem, clone) {
    var children = elem.childNodes;
    for (var ix = 0; ix < children.length; ix++) {
        var c = children[ix];
        if (c.namespaceURI === com.sweattrails.api.xmlns) {
            switch (c.localName) {
                case "field":
                    form.addField(new com.sweattrails.api.FormField(c, (form.layout === "table") ? null : clone));
                    break;
                case "action":
                    form.footer.buildAction(c);
                    break;
                case "header":
                    form.header.build(c, (form.layout === "table") ? null : clone);
                    break;
                case "footer":
                    form.footer.build(c, (form.layout === "table") ? null : clone);
                    break;
            }
        } else {
            var childClone = c.cloneNode(false);
            clone.appendChild(childClone);
            this.copyNode(form, c, childClone);
        }
    }
};

new com.sweattrails.api.FormBuilder();

/**
 * FormField - Abstract base class for form elements
 */

com.sweattrails.api.internal.fieldtypes = {};

com.sweattrails.api.FormField = function(elem, parent) {
    this.type = "formfield";
    this.id = elem.getAttribute("id") || elem.getAttribute("property");
    this.hidden = false;
    this.modes = elem.getAttribute("mode");
    this.readonly = elem.getAttribute("readonly") === "true";
    this.setType(elem);
    $$.register(this);

    // A FormField is mute when it doesn't interact with the data bridge
    // at all. So it doesn't get any. An example is a header field.
    if ((typeof(this.impl.isMute) === "undefined") || !this.impl.isMute()) {
        this.bridge = new com.sweattrails.api.internal.DataBridge();
        var p = elem.getAttribute("property");
        if (p) {
            this.bridge.get = p;
        } else if (elem.getAttribute("get")) {
            this.bridge.get = __.getfunc(elem.getAttribute("get"));
            this.bridge.set = elem.getAttribute("set");
        } else {
            this.bridge.get = this.id;
        }
    } else {
        this.bridge = null;
    }
    this.parent = parent;
    var onchange = elem.getAttribute("onchange");
    if (onchange) {
        this.onchange = __.getfunc(onchange);
    }
    var oninput = elem.getAttribute("oninput");
    if (oninput) {
        this.oninput = __.getfunc(oninput);
    }
    if (elem.getAttribute("validate")) {
        this.validator = __.getfunc(elem.getAttribute("validate"));
    }
    this.label = elem.getAttribute("label") || elem.getAttribute("verbose_name") || this.id;
    this.required = elem.getAttribute("required") === "true";
    var v = elem.getAttribute("value") || elem.getAttribute("default");
    if (v) {
        this.defval = __.getfunc(v) || v;
    }
    this.placeholder = elem.getAttribute("placeholder");
    return this;
};

com.sweattrails.api.FormField.prototype.setType = function(elem) {
    var type = elem.getAttribute("type");
    var datatype = elem.getAttribute("datatype");
    var factory = null;
    if (hasChildWithTagNameNS(elem, com.sweattrails.api.xmlns, "value") || hasChildWithTagNameNS(elem, com.sweattrails.api.xmlns, "choices")) {
        factory = com.sweattrails.api.LookupField;
    } else {
        if (type) {
            factory = com.sweattrails.api.internal.fieldtypes[type];
        }
        if (!factory && datatype) {
            factory = com.sweattrails.api.internal.fieldtypes[datatype];
        }
    }
    if (!factory) {
        $$.log(this, "TYPE " + type + " NOT REGISTERED!");
        $$.log(this, "REGISTRY:");
        for (var t in com.sweattrails.api.internal.fieldtypes) {
            $$.log(this, "  " + t + "==" ? (type === t) : "!=");
        }
        factory = com.sweattrails.api.internal.fieldtypes.text;
    }
    this.impl = new factory(this, elem);
    this.impl.elem = elem;
    this.impl.field = this;
};

com.sweattrails.api.FormField.prototype.postprocess = function() {
    if (this.impl.postprocess) {
        this.impl.postprocess();
    }
};

com.sweattrails.api.FormField.prototype.getElementID = function() {
    var a = ["forms", this.form.id, this.id];
    if (arguments.length > 0) {
        a = a.concat(Array.prototype.slice.call(arguments));
    }
    return a.join("-");
}

com.sweattrails.api.FormField.prototype.render = function(mode, object) {
    if (this.modes && (this.modes.length > 0) && (this.modes.indexOf(mode) < 0)) {
	    return false;
    }
    this.mode = mode;
    var val = this.getValueFromObject(object);
    var elem = null;
    if ((this.mode !== com.sweattrails.api.MODE_VIEW) && !this.readonly) {
        elem = this.impl.renderEdit(val);
    } else if ((this.mode === com.sweattrails.api.MODE_VIEW) || this.readonly) {
        elem = this.impl.renderView(val);
    }
    if (!elem.id) {
        elem.id = this.getElementID();
    }
    if ((elem.tagName in ["input", "img", "textarea", "select"]) && !elem.name) {
        elem.name = this.id;
    }
    if (this.form.layout !== "table") {
        if (this.element) {
            this.parent.removeChild(this.element);
        }
        this.element = elem;
        this.parent.appendChild(this.element);
    } else {
        if (this.element && this.form.table) {
            this.form.table.removeChild(this.element);
        }
        var tr = null;
        var td = null;
        if (this.errors) {
            tr = this.form.newTR();        	
            td = document.createElement("td");
            td.colspan = 2;
            td.className = "validationerrors";
            tr.appendChild(td);
            var ul = document.createElement("ul");
            ul.appendChild(td);
            this.errors.forEach(function (e) {
            	var li = document.createElement("li");
            	li.className = "validationerror";
            	li.innerHTML = e.message;
            	ul.appendChild(li);
            });
        }
        tr = this.form.newTR();
        var lbl;
        if (typeof(this.impl.getLabel) === "function") {
            lbl = this.impl.getLabel();
        } else {
            lbl = this.label;
        }

        td = document.createElement("td");
        td.className = "formlabel";
        tr.appendChild(td);
        var label = document.createElement("label");
        label.htmlFor = this.id;
        label.innerHTML = (this.required) ? "(*) " + lbl + ":" : lbl + ":";;
        td.appendChild(label);
        td = document.createElement("td");

        td.className = "formdata";
        if (typeof(this.impl.colspan) !== "undefined") {
            td.colspan = this.impl.colspan();
        } else {
            if (!lbl) {
                td.colspan = 2;
            }
        }
        td.appendChild(elem);
        tr.appendChild(td);
        this.element = tr;
        this.element.id =  this.getElementID("fld", "container");
    }
    this.element.hidden = this.hidden;
    return true;
};

com.sweattrails.api.FormField.prototype.erase = function() {
    this.impl.erase && this.impl.erase();
};

Object.defineProperty(com.sweattrails.api.FormField.prototype, "hidden", {
    get: function() { return this._hidden; },
    set: function(h) {
        this._hidden = h;
        if (this.element) this.element.hidden = h;
    }
});

com.sweattrails.api.FormField.prototype.validate = function() {
    this.errors = null;
    if (this.impl.validator) {
    	ST_int.buildErrors(this, this.impl.validator());
    }
    if (this.validator) {
        ST_int.buildErrors(this, this.validator());
    }
    return this.errors;
};

com.sweattrails.api.FormField.prototype.clear = function() {
    this.impl.clear && this.impl.clear();
};

com.sweattrails.api.FormField.prototype.setValue = function(value) {
    this.impl.setValue && this.impl.setValue(value);
};

com.sweattrails.api.FormField.prototype.onValueChange = function() {
    if (this.onchange) {
        var val = this.impl.getValueFromControl();
        this.onchange(val);
    }
};

com.sweattrails.api.FormField.prototype.onInput = function() {
    if (this.oninput) {
        var val = this.impl.getValueFromControl();
        this.oninput(val);
    }
};

com.sweattrails.api.FormField.prototype.assignValueToObject = function(object) {
    $$.log(this, "assignValueToObject");
    if (this.bridge) {
        this.impl.setValueFromControl(this.bridge, object);
    }
};

com.sweattrails.api.FormField.prototype.getValueFromObject = function(object) {
    var ret = null;
    if (this.bridge) {
        ret = this.bridge.getValue(object);
        if (!ret && this.defval) {
            if (typeof(this.defval) === 'function') {
                ret = this.defval(object);
            } else {
                ret = this.defval;
            }
        }
    }
    return ret;
};

/*
 * TitleField - 
 */

com.sweattrails.api.TitleField = function(fld, elem) {
    this.text = elem.getAttribute("text");
    this.level = elem.getAttribute("level") || "3";
};

com.sweattrails.api.TitleField.prototype.renderEdit = function() {
    this.control = document.createElement("h" + this.level);
    this.control.innerHTML = this.text;
    return this.control;
};

com.sweattrails.api.TitleField.prototype.renderView = function() {
    return this.renderEdit();
};

com.sweattrails.api.TitleField.prototype.colspan = function() {
    return 2;
};

com.sweattrails.api.TitleField.prototype.getLabel = function() {
    return null;
};

com.sweattrails.api.TitleField.prototype.isMute = function() {
    return true;
};

/*
 * LabelField -
 */

com.sweattrails.api.LabelField = function(fld, elem) {
    this.linkedfieldid = elem.getAttribute("field");
    console.assert(this.linkedfieldid, "Label field requires a 'field' attribute")
    if (!fld.id) {
        fld.id = this.linkedfieldid + "-label";
    }
    this.linkedfield = null;
};

com.sweattrails.api.LabelField.prototype.renderEdit = function() {
    if (!this.linkedfield) {
        this.linkedfield = this.field.form.$[this.linkedfieldid];
        console.assert(this.linkedfield, "LabelField: could not resolve field %s", this.linkedfieldid);
    }
    var lbl = this.linkedfield.label;
    var label = document.createElement("label");
    label.htmlFor = this.linkedfield.getElementID();
    label.innerHTML = (this.linkedfield.required) ? "(*) " + lbl + ":" : lbl + ":";;
    this.control = label;
    return this.control;
};

com.sweattrails.api.LabelField.prototype.renderView = function() {
    return this.renderEdit();
};

com.sweattrails.api.LabelField.prototype.colspan = function() {
    return 1;
};

com.sweattrails.api.LabelField.prototype.getLabel = function() {
    return null;
};

com.sweattrails.api.LabelField.prototype.isMute = function() {
    return true;
};

com.sweattrails.api.LabelField.prototype.postprocess = function() {

};

/*
 * Control factories -
 */

com.sweattrails.api.internal.buildInput = function(type) {
    var control = document.createElement("input");
    control.type = type;
    if (arguments.length > 2) {
        control.value = arguments[2] ? arguments[2] : "";
    }
    if (arguments.length > 1) {
        var elem = arguments[1];
        if (elem.hasAttribute("size")) {
            control.size = elem.getAttribute("size");
        }
        if (elem.hasAttribute("maxlength")) {
            control.maxLength = elem.getAttribute("maxlength");
        }
        if (elem.hasAttribute("regexp")) {
            control.pattern = "/" + elem.getAttribute("regexp") + "/";
        }
        if (elem.hasAttribute("placeholder")) {
            control.placeholder = elem.getAttribute("placeholder");
        }
        control.required = elem.getAttribute("required");
    }
    return control;
};

com.sweattrails.api.internal.buildTextInput = function(elem, value) {
    return com.sweattrails.api.internal.buildInput("text", elem, value);
};

/*
 * TextField -
 */

com.sweattrails.api.TextField = function() {
    this.type = "text";
};

com.sweattrails.api.TextField.prototype.renderEdit = function(value) {
    this.control = com.sweattrails.api.internal.buildInput("text", this.elem, value);
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    return this.control;
};

com.sweattrails.api.TextField.prototype.setValueFromControl = function(bridge, object) {
    $$.log(this.field, "setting value %s", this.control.value);
    bridge.setValue(object, this.control.value);
};

com.sweattrails.api.TextField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    ret.innerHTML = value || "";
    return ret;
};

com.sweattrails.api.TextField.prototype.clear = function() {
    this.setValue("");
};

com.sweattrails.api.TextField.prototype.setValue = function(value) {
    if (this.control) {
        this.control.value = (value) ? value : "";
    }
};

/*
 * PasswordField -
 */

com.sweattrails.api.PasswordField = function(fld, elem) {
    this.type = "text";
    this.confirm = elem.getAttribute("confirm") && (elem.getAttribute("confirm") === "true");
};

com.sweattrails.api.PasswordField.prototype.renderEdit = function(value) {
    this.div = document.createElement("div");
    this.div.id = this.field.getElementID("container");
    this.control = com.sweattrails.api.internal.buildInput("password", this.elem, "");
    this.control.value =  "";
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.input = this.field.onInput.bind(this.field);
    this.control.name = this.field.id;
    this.div.appendChild(this.control);
    if (this.confirm) {
        this.check = com.sweattrails.api.internal.buildInput("password", this.elem, "");
        this.check.id = this.field.getElementID() + "-confirm";
        this.check.name = this.field.id + "-confirm";
	    this.div.appendChild(this.check);
    }
    return this.div;
};

com.sweattrails.api.PasswordField.prototype.validate = function() {
    if (this.confirm && (this.control.value !== this.check.value)) {
	    return "Password values do not match";
    } else {
	    return null;
    }
};

com.sweattrails.api.PasswordField.prototype.clear = function() {
    this.setValue("");
};

com.sweattrails.api.PasswordField.prototype.setValue = function(value) {
    if (this.control) {
        this.control.value = value;
        if (this.confirm && this.check) {
            this.check.value = value;
        }
    }
};

com.sweattrails.api.PasswordField.prototype.setValueFromControl = function(bridge, object) {
    this.value = this.control.value;
    bridge.setValue(object, this.control.value);
};

com.sweattrails.api.PasswordField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    ret.innerHTML = "*******";
    return ret;
};

/*
 * WeightField -
 */

com.sweattrails.api.WeightField = function(fld, elem) {
    this.type = "number";
    this.field = fld;
};

com.sweattrails.api.WeightField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span");
    this.span = this.field.getElementID("container");
    this.control = document.createElement("input");
    var w = null;
    if (value) {
        w = weight(parseFloat(value), native_unit, false);
    }
    this.control.value = w || "";
    this.control.type = "text";
    this.control.maxLength = 6;
    this.control.size = 4; // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    this.control.id = this.field.getElementID();
    this.control.name = this.id;
    this.span.appendChild(this.control);
    this.unitSelector = document.createElement("select");
    this.unitSelector.id = this.field.getElementID("units");
    this.unitSelector.name = this.field.id + "-units";
    this.nativeUnitIndex = (native_unit === "m") ? 0 : 1;
    var option = document.createElement("option");
    option.selected = (native_unit === "m");
    option.value = "1.0";
    option.text = "kg";
    this.unitSelector.appendChild(option);
    option = document.createElement("option");
    option.selected = (native_unit === "i");
    option.value = "2.20462262";
    option.text = "lbs";
    this.unitSelector.onchange = this.field.onValueChange.bind(this.field);
    this.unitSelector.appendChild(option);
    this.span.appendChild(this.unitSelector);
    return this.span;
};

com.sweattrails.api.WeightField.prototype.setValueFromControl = function(bridge, object) {
    this.value = parseFloat(this.control.value) / parseFloat(this.unitSelector.value);
    bridge.setValue(object, this.value);
};

com.sweattrails.api.WeightField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    var w = null;
    if (value) {
        w = weight(parseFloat(value), native_unit, true);
    }
    ret.innerHTML = w || "";
    return ret;
};

com.sweattrails.api.WeightField.prototype.clear = function() {
    if (this.control) {
        this.control.value = "";
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

com.sweattrails.api.WeightField.prototype.setValue = function(value) {
    // FIXME: This assumes the value set is in the user's native unit. This is 
    // probably wrong. It's probably in the system unit.
    if (this.control) {
        this.control.value = value;
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

/*
 * LengthField -
 */

com.sweattrails.api.LengthField = function(fld, elem) {
    this.type = "number";
    this.field = fld;
};

com.sweattrails.api.LengthField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span");
    this.span.id = this.field.getElementID("-container");
    this.control = document.createElement("input");
    var l = null;
    if (value) {
        l = length(parseFloat(value), native_unit, false);
    }
    this.control.value = l || "";
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "text";
    this.control.maxLength = 6;
    this.control.size = 4; // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    this.control.id = this.field.getElementID();
    this.control.name = this.id;
    this.span.appendChild(this.control);
    this.nativeUnitIndex = (native_unit === "m") ? 0 : 1;
    this.unitSelector = document.createElement("select");
    this.unitSelector.name = this.field.id + "-units";
    this.unitSelector.id = this.field.getElementID("-units");
    var option = document.createElement("option");
    option.selected = (native_unit === "m");
    option.value = "1.0";
    option.text = "cm";
    this.unitSelector.appendChild(option);
    option = document.createElement("option");
    option.selected = (native_unit === "i");
    option.value = "0.393700787";
    option.text = "in";
    this.unitSelector.appendChild(option);
    this.unitSelector.onchange = this.field.onValueChange.bind(this.field);
    this.span.appendChild(this.unitSelector);
    return this.span;
};

com.sweattrails.api.LengthField.prototype.setValueFromControl = function(bridge, object) {
    this.value = parseFloat(this.control.value) / parseFloat(this.unitSelector.value);
    var v = this.control.value;
    if (v) {
        v = v.trim();
        if ((this.unitSelector.value !== 1.0) && (v.indexOf("'") > 0)) {
            var a = v.split("'");
            v = 12*parseInt(a[0].trim()) + parseInt(a[1].trim());
        } else {
            v = parseFloat(v);
        }
        this.value = v / parseFloat(this.unitSelector.value);
    } else {
        this.value = 0;
    }
    bridge.setValue(object, this.value);
};

com.sweattrails.api.LengthField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    var l = null;
    if (value) {
        l = length(parseFloat(value), native_unit, true);
    }
    ret.innerHTML = l || "";
    return ret;
};

com.sweattrails.api.LengthField.prototype.clear = function() {
    if (this.control) {
        this.control.value = "";
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

com.sweattrails.api.LengthField.prototype.setValue = function(value) {
    // FIXME: This assumes the value set is in the user's native unit. This is 
    // probably wrong. It's probably in the system unit.
    if (this.control) {
        this.control.value = value;
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

/*
 * DistanceField -
 */

com.sweattrails.api.DistanceField = function(fld, elem) {
    this.type = "number";
    this.field = fld;
};

com.sweattrails.api.DistanceField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span");
    this.span.id = this.field.getElementID("container");
    this.control = document.createElement("input");
    var l = null;
    if (value) {
        l = length(parseFloat(value), native_unit, false);
    }
    this.control.value = l || "";
    this.control.name = this.field.id;
    this.control.id = this.field.getElementID();
    this.control.type = "text";
    this.control.maxLength = 6;
    this.control.size = 6; // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    this.span.appendChild(this.control);
    this.nativeUnitIndex = (native_unit === "m") ? 0 : 1;
    this.unitSelector = document.createElement("select");
    this.unitSelector.id = this.field.getElementID("units");
    this.unitSelector.name = this.field.id + "-units";
    var option = document.createElement("option");
    option.selected = (native_unit === "m");
    option.value = "1000";
    option.text = "km";
    this.unitSelector.appendChild(option);
    option = document.createElement("option");
    option.selected = (native_unit === "i");
    option.value = "1608";
    option.text = "mile";
    this.unitSelector.appendChild(option);
    this.unitSelector.onchange = this.field.onValueChange.bind(this.field);
    this.span.appendChild(this.unitSelector);
    return this.span;
};

com.sweattrails.api.DistanceField.prototype.setValueFromControl = function(bridge, object) {
    this.value = parseFloat(this.control.value) / parseFloat(this.unitSelector.value);
    var v = this.control.value;
    if (v) {
        v = v.trim();
        this.value = parseFloat(v) * parseFloat(this.unitSelector.value);
    } else {
        this.value = 0;
    }
    bridge.setValue(object, this.value);
};

com.sweattrails.api.DistanceField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    var l = null;
    if (value) {
        l = distance(parseFloat(value) / 1000.0, native_unit, true);
    }
    ret.innerHTML = l || "";
    return ret;
};

com.sweattrails.api.DistanceField.prototype.clear = function() {
    if (this.control) {
        this.control.value = "";
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

com.sweattrails.api.DistanceField.prototype.setValue = function(value) {
    // FIXME: This assumes the value set is in the user's native unit. This is 
    // probably wrong. It's probably in the system unit.
    if (this.control) {
        this.control.value = value;
    }
    if (this.unitSelector) {
        this.unitSelector.selectedIndex = this.nativeUnitIndex;
    }
};

/*
 * CheckBoxField -
 */

com.sweattrails.api.CheckBoxField = function() {
    this.type = "boolean";
};

com.sweattrails.api.CheckBoxField.prototype.renderEdit = function(value) {
    this.control = com.sweattrails.api.internal.buildInput("checkbox", this.field.id, this.elem);
    this.control.value = true;
    this.control.checked = value;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    return this.control;
};

com.sweattrails.api.CheckBoxField.prototype.setValueFromControl = function(bridge, object) {
    this.value = this.control.checked;
    bridge.setValue(object, this.value);
};

com.sweattrails.api.CheckBoxField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    if (value) {
        var img = document.createElement("img");
        img.src = "/image/checkmark.png";
        img.height = 24;
        img.width = 24;
        ret.appendChild(img);
    } else {
	    ret.innerHTML = "&#160;";
    }
    return ret;
};

com.sweattrails.api.CheckBoxField.prototype.clear = function() {
    this.setValue(false)
};

com.sweattrails.api.CheckBoxField.prototype.setValue = function(value) {
    if (this.control) {
        this.control.checked = value;
    }
};

/*
 * DateTimeField -
 */

com.sweattrails.api.DateTimeField = function(fld, elem) {
    this.type = "datetime";
    this.field = fld;
    this.date = this.time = true;
    if (elem && elem.getAttribute("timeformat")) {
        this.timeformat = elem.getAttribute("timeformat");
    } else {
        this.timeformat = "timeofday";
    }
};

com.sweattrails.api.DateTimeField.prototype.renderEdit = function(value) {
    var span = document.createElement("span");
    span.id = this.field.getElementID("container");
    var d = obj_to_datetime(value);
    var type;
    if (this.date && !this.time) {
        type = "date";
    } else if (this.time && !this.date) {
        type = "time";
    } else {
        type = "datetime";
    }
    this.control = com.sweattrails.api.internal.buildInput(type);
    d && (this.control.valueAsDate = d);
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    this.control.id = this.field.getElementID();
    this.control.name = this.field.id;
    span.appendChild(this.control);
    
    return span;
};

com.sweattrails.api.DateTimeField.prototype.setValueFromControl = function(bridge, object) {
    v = this.control.valueAsDate;
    this.value = (v) ? datetime_to_obj(v) : null;
    bridge.setValue(object, this.value);
};

com.sweattrails.api.DateTimeField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    var t;

    if (typeof(value.hour) === "undefined") {
        value = seconds_to_timeobj(value)
    }
    if (value) {
        if (this.time) {
            if ((typeof(this.timeformat) !== "undefined") && (this.timeformat === "duration")) {
                t = prettytime(value);
            } else {
                t = format_time(value);
            }
        } else {
            t = "";
        }
        ret.innerHTML = (this.date && (format_date(value) + " ") || "") + t;
    } else {
        ret.innerHTML = "&#160;";
    }
    return ret;
};

com.sweattrails.api.DateTimeField.prototype.clear = function() {
    this.setValue(null);
};

com.sweattrails.api.DateTimeField.prototype.setValue = function(value) {
    if (this.control) {
        this.control.valueAsDate = value;
    }
};

/*
 * DateField - Use DateTimeField, just without the time bits
 */

com.sweattrails.api.DateField = function(fld, elem) {
    com.sweattrails.api.DateTimeField.call(this, fld, elem);
    this.time = false;
};

com.sweattrails.api.DateField.prototype = new com.sweattrails.api.DateTimeField();

/*
 * TimeField - Use DateTimeField, just without the date bits
 */

com.sweattrails.api.TimeField = function(fld, elem) {
    com.sweattrails.api.DateTimeField.call(this, fld, elem);
    this.date = false;
};

com.sweattrails.api.TimeField.prototype = new com.sweattrails.api.DateTimeField();

/*
 * FileField -
 */

com.sweattrails.api.FileField = function(fld, elem) {
    this.type = "file";
    this.multiple = elem.getAttribute("multiple") === "true";
};

com.sweattrails.api.FileField.prototype.renderEdit = function(value) {
    this.control = com.sweattrails.api.internal.buildInput("file");
    if (this.multiple) this.control.multiple = true;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.control.oninput = this.field.onInput.bind(this.field);
    return this.control;
};

com.sweattrails.api.FileField.prototype.setValueFromControl = function(bridge, object) {
    var files = this.control.files;
    if (files) {
        if (this.multiple) {
            $$.log(this.field, "#files: %d", files.length)
            for (var ix = 0; ix < files.length; ix++) {
                $$.log(this.field, "file[%d]: %s", ix, files[ix].name);
            }
        } else {
            $$.log(this.field, "file: %s", files[0].name);
        }
    } else {
        $$.log(this.field, "this.control.files undefined...");
    }
    this.value = (this.multiple) ? this.control.files : this.control.files[0];
    bridge.setValue(object, this.value);
};

/* TODO Better presentation (MIME type icons) */
com.sweattrails.api.FileField.prototype.renderView = function(value) {
    var ret = document.createElement("span");
    ret.innerHTML = "<i>... File ...</i>";
    return ret;
};

com.sweattrails.api.FileField.prototype.clear = function() {
    this.setValue(null);
};

com.sweattrails.api.FileField.prototype.setValue = function(value) {
    // FIXME..
    if (this.control) {
        console.log(" FileField.setValue not implemented...");
    }
};

/*
 * IconField -
 */

com.sweattrails.api.IconField = function(fld, elem) {
    this.field = fld;
    this.height = elem.getAttribute("height") || 48;
    this.width = elem.getAttribute("width") || 48;
    this.datasource = com.sweattrails.api.dataSourceBuilder.build(elem);
    if (this.datasource) {
        // this.submitParameter(elem.getAttribute("imageparameter") || "image",
        //     (function() {return this.control.files[0];}).bind(this));
        // this.submitParameter(elem.getAttribute("contenttypeparameter") || "contentType",
        //     (function() {return this.control.files[0].type;}).bind(this));
        this.datasource.submitAsJSON = false;
        this.datasource.addView(this);
    }
    fld.readonly = true;
};

com.sweattrails.api.IconField.prototype.renderEdit = function(value) {
    return null;
};

com.sweattrails.api.IconField.prototype.getValueFromControl = function(bridge, object) {
    return null;
};

com.sweattrails.api.IconField.prototype.renderView = function(value) {
    var div = document.createElement("div");
    if (this.url && (this.field.mode === com.sweattrails.api.MODE_VIEW)) {
        var onDragEnter = function() {
            this.entered++;
            this.control.style.display='block';
        };
        var onDragLeave = function() {
            this.entered--;
            if (!this.entered) this.control.style.display='none';
        };
        div.ondragenter = onDragEnter.bind(this);
        div.ondragleave = onDragLeave.bind(this);
    }

    var img = document.createElement("img");
    img.src = value;
    img.height = this.height;
    img.width = this.width;
    div.appendChild(img);

    if (this.datasource && (this.field.mode === com.sweattrails.api.MODE_VIEW)) {
        this.control = document.createElement("input");
        this.control.name = this.field.id;
        this.control.id = this.field.id;
        this.control.type = "file";
        this.control.style.display = "none";
        this.control.style.position = "absolute";
        this.control.style.top = this.control.style.left = this.control.style.right = this.control.style.bottom = 0;
        this.control.style.opacity = 0;

        var submitFnc = function() {
            this.datasource.createObjectFrom(this.field.form.datasource.getObject());
            this.datasource.submit();
        };
        this.control.onchange = submitFnc.bind(this);
        div.appendChild(this.control);
    }
    return div;
};

com.sweattrails.api.IconField.prototype.onDataSubmitted = function() {
    this.field.form.render();
};

com.sweattrails.api.IconField.prototype.onDataError = function() {
    this.field.form.render();
};

com.sweattrails.api.internal.fieldtypes.text = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.TextProperty = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.StringProperty = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.LinkProperty = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.title = com.sweattrails.api.TitleField;
com.sweattrails.api.internal.fieldtypes.label = com.sweattrails.api.LabelField;
com.sweattrails.api.internal.fieldtypes.password = com.sweattrails.api.PasswordField;
com.sweattrails.api.internal.fieldtypes.PasswordProperty = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.integer = com.sweattrails.api.IntField;
com.sweattrails.api.internal.fieldtypes.integer = com.sweattrails.api.IntField;
com.sweattrails.api.internal.fieldtypes.weight = com.sweattrails.api.WeightField;
com.sweattrails.api.internal.fieldtypes.length = com.sweattrails.api.LengthField;
com.sweattrails.api.internal.fieldtypes.distance = com.sweattrails.api.DistanceField;

com.sweattrails.api.internal.fieldtypes.checkbox = com.sweattrails.api.CheckBoxField;
com.sweattrails.api.internal.fieldtypes.boolean = com.sweattrails.api.CheckBoxField;
com.sweattrails.api.internal.fieldtypes.bool = com.sweattrails.api.CheckBoxField;
com.sweattrails.api.internal.fieldtypes.BooleanProperty = com.sweattrails.api.CheckBoxField;

com.sweattrails.api.internal.fieldtypes.date = com.sweattrails.api.DateField;
com.sweattrails.api.internal.fieldtypes.DateProperty = com.sweattrails.api.DateField;
com.sweattrails.api.internal.fieldtypes.datetime = com.sweattrails.api.DateTimeField;
com.sweattrails.api.internal.fieldtypes.DateTimeProperty = com.sweattrails.api.DateTimeField;
com.sweattrails.api.internal.fieldtypes.time = com.sweattrails.api.TimeField;
com.sweattrails.api.internal.fieldtypes.TimeProperty = com.sweattrails.api.TimeField;

com.sweattrails.api.internal.fieldtypes.file = com.sweattrails.api.FileField;
com.sweattrails.api.internal.fieldtypes.icon = com.sweattrails.api.IconField;
com.sweattrails.api.internal.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
com.sweattrails.api.internal.fieldtypes.lookup = com.sweattrails.api.LookupField;
com.sweattrails.api.internal.fieldtypes.choice = com.sweattrails.api.LookupField;

