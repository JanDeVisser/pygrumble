/**
 * Form -
 */

com.sweattrails.api.MODE_VIEW = "view";
com.sweattrails.api.MODE_EDIT = "edit";
com.sweattrails.api.MODE_NEW = "new";

function st_show_form() {
    var formname = arguments[0];
    var mode = ((arguments.length > 1) && arguments[1]) ? arguments[1] : com.sweattrails.api.MODE_NEW;
    var form = $(formname);
    if (form && !form.ispopup) {
        form.popup(mode);
    }
}

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
    	for (var ix in e) {
    	    ST_int.buildErrors(e[ix]);
    	}
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
    this.header.erase();
    this.footer.erase();
    var ix;
    if (this.renderedFields) {
        for (ix in this.renderedFields) {
            this.renderedFields[ix].erase();
        }
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
    for (ix in this.fields) {
    	var f = this.fields[ix];
        f.element = null;
        if (f.render(this.mode, obj)) {
            this.renderedFields.push(f);
        }
    }
    this.footer.render();
};

com.sweattrails.api.Form.prototype.applyData = function() {
    if (this.mode !== com.sweattrails.api.MODE_NEW) {
        this.datasource.reset();
        this.datasource.next();
    }
    var obj = this.datasource.getObject();
    for (var fix in this.renderedFields) {
        var f = this.renderedFields[fix];
        if (!f.readonly) {
            f.assignValueToObject(obj);
        }
    }
    if (typeof(this.prepare) === "function") {
        this.prepare(obj);
    }
};

com.sweattrails.api.Form.prototype.submit = function() {
    this.errors = [];
    if (this.validator) {
        ST_int.buildErrors(this, this.validator());
    }
    var f = null;
    for (var fix in this.renderedFields) {
    	f = this.renderedFields[fix];
        f.errors = f.validate();
        if (f.errors) this.errors = this.errors.concat(f.errors);
    }
    if (this.errors.length > 0) {
        this.render(this.mode);
    } else {
        this.applyData();
        this.progress(this.submitMessage);
        console.log("Submitting form " + this.id);
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
            this.render(com.sweattrails.api.MODE_VIEW);
        }
    } finally {
        this.ispopup = false;
    }
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
    handled = false;
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
    this.buildForm(form, f);
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
    if (elem.getAttribute("mode")) {
        form.init_mode = elem.getAttribute("mode");
    }
    if (elem.getAttribute("initialize")) {
        form.initialize = getfunc(elem.getAttribute("initialize"));
    }
    if (elem.getAttribute("onsubmitted")) {
        form.onsubmitted = getfunc(elem.getAttribute("onsubmitted"));
    }
    if (elem.getAttribute("validate")) {
        this.validator = getfunc(elem.getAttribute("validate"));
    }
    if (elem.getAttribute("onerror")) {
        form.onerror = getfunc(elem.getAttribute("onerror"));
    }
    if (elem.getAttribute("onredirect")) {
        form.onredirect = getfunc(elem.getAttribute("onredirect"));
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
    var fields = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "field");
    for (var j = 0; j < fields.length; j++) {
        new com.sweattrails.api.FormField(form, fields[j]);
    }
    form.footer.build(elem);
    var footer = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "footer");
    if (footer.length) {
        form.footer.build(footer[0]);
    }
    var header = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "header");
    if (header.length) {
        form.header.build(header[0]);
    }
};

new com.sweattrails.api.FormBuilder();

/**
 * FormField - Abstract base class for form elements
 */

com.sweattrails.api.internal.fieldtypes = {};

com.sweattrails.api.FormField = function(form, f) {
    this.hidden = false;
    if (f) {
        this.type = "formfield";
	this.id = f.getAttribute("id") || f.getAttribute("property");
	$$.register(this);
	this.modes = f.getAttribute("mode");
	this.readonly = f.getAttribute("readonly") === "true";
	this.setType(f.getAttribute("type"), f);
        
        // A FormField is mute when it doesn't interact with the data bridge
        // at all. So it doesn't get any.
        if ((typeof(this.impl.isMute) === "undefined") || !this.impl.isMute()) {
            this.bridge = new com.sweattrails.api.internal.DataBridge();
            var p = f.getAttribute("property");
            if (p) {
                this.bridge.get = p;
            } else if (f.getAttribute("get")) {
                this.bridge.get = getfunc(f.getAttribute("get"));
                this.bridge.set = f.getAttribute("set");
            } else {
                this.bridge.get = this.id;
            }
        } else {
            this.bridge = null;
        }
	var onchange = f.getAttribute("onchange");
	if (onchange) {
	    this.onchange = getfunc(onchange);
	}
	if (f.getAttribute("validate")) {
	    this.validator = getfunc(f.getAttribute("validate"));
	}
	this.label = f.getAttribute("label");
	this.required = f.getAttribute("required") === "true";
	if (f.getAttribute("value")) {
            var v = f.getAttribute("value");
            this.defval = getfunc(v) || v;
        }
    }
    form.addField(this);
    return this;
};

com.sweattrails.api.FormField.prototype.setType = function(type, elem) {
    type = type || "text";
    var factory = com.sweattrails.api.internal.fieldtypes[type];
    if (!factory) {
        $$.log(this, "TYPE " + type + " NOT REGISTERED!");
        $$.log(this, "REGISTRY:");
        for (t in com.sweattrails.api.internal.fieldtypes) {
            $$.log(this, "  " + t + "==" ? (type === t) : "!=");
        }
        factory = com.sweattrails.api.internal.fieldtypes.text;
    }
    this.impl = new factory(this, elem);
    this.impl.field = this;
};

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
    if (this.parent) {
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
            for (eix in this.errors) {
            	var li = document.createElement("li");
            	li.className = "validationerror";
            	li.innerHTML = this.errors[eix].message;
            	ul.appendChild(li);
            }
        }
        tr = this.form.newTR();
        var lbl;
        if (typeof(this.impl.getLabel) === "function") {
            lbl = this.impl.getLabel();
        } else {
            lbl = this.label || this.id;
        }
        if (lbl) {
            lbl = (this.required) ? "(*) " + lbl + ":" : lbl + ":";
            td = document.createElement("td");
            td.style.textAlign = "right";
            td.width = this.width || "auto";
            var label = document.createElement("label");
            label.htmlFor = this.id;
            label.innerHTML = lbl;
            td.appendChild(label);
            tr.appendChild(td);
        }
        td = document.createElement("td");
        td.style.textAlign = "left";
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
        this.element.id = this.id + "-fld-container";
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

com.sweattrails.api.FormField.prototype.assignValueToObject = function(object) {
    $$.log(this, "setValue");
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
    this.field = fld;
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
 * TextField -
 */

com.sweattrails.api.TextField = function(fld, elem) {
    this.field = fld;
    this.size = elem.getAttribute("size");
    this.maxlength = elem.getAttribute("maxlength");
};

com.sweattrails.api.TextField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input");
    this.control.value = value || "";
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "text";
    if (this.size) {
        this.control.size = this.size;
    }
    if (this.maxlength) {
        this.control.maxLength = this.maxlength;
    }
    this.control.onchange = this.field.onValueChange.bind(this.field);
    return this.control;
};

com.sweattrails.api.TextField.prototype.setValueFromControl = function(bridge, object) {
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
        this.control.value = value;
    }
};

/*
 * PasswordField -
 */

com.sweattrails.api.PasswordField = function(fld, elem) {
    this.field = fld;
    this.confirm = elem.getAttribute("confirm") && (elem.getAttribute("confirm") === "true");
};

com.sweattrails.api.PasswordField.prototype.renderEdit = function(value) {
    this.div = document.createElement("div");
    this.control = document.createElement("input");
    this.control.value =  "";
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "password";
    if (this.size) this.control.size = this.size;
    if (this.maxlength) this.control.maxLength = this.maxlength;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.div.appendChild(this.control);
    if (this.confirm) {
	this.check = document.createElement("input");
	this.check.value =  "";
	this.check.name = this.field.id + "-check";
	this.check.id = this.field.id + "-check";
	this.check.type = "password";
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
        if (this.confirm) {
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
    this.field = fld;
};

com.sweattrails.api.WeightField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span");
    this.control = document.createElement("input");
    var w = null;
    if (value) {
        w = weight(parseFloat(value), native_unit, false);
    }
    this.control.value = w || "";
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "text";
    this.control.maxLength = 6;
    this.control.size = 4; // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field);
    this.span.appendChild(this.control);
    this.unitSelector = document.createElement("select");
    this.unitSelector.name = this.field.id + "-units";
    this.unitSelector.id = this.unitSelector.name;
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
    this.field = fld;
};

com.sweattrails.api.LengthField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span");
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
    this.span.appendChild(this.control);
    this.nativeUnitIndex = (native_unit === "m") ? 0 : 1;
    this.unitSelector = document.createElement("select");
    this.unitSelector.name = this.field.id + "-units";
    this.unitSelector.id = this.unitSelector.name;
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
 * CheckBoxField -
 */

com.sweattrails.api.CheckBoxField = function(fld, elem) {
    this.field = fld;
};

com.sweattrails.api.CheckBoxField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input");
    this.control.value = true;
    this.control.checked = value;
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "checkbox";
    this.control.onchange = this.field.onValueChange.bind(this.field);
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
    this.field = fld;
    this.date = this.time = true;
};

com.sweattrails.api.DateTimeField.prototype.renderEdit = function(value) {
    var span = document.createElement("span");
    var d = obj_to_datetime(value);
    this.control = document.createElement("input");
    this.control.name = this.field.id + "-date";
    this.control.id = this.control.name;
    if (this.date && !this.time) {
        this.control.type = "date";
    } else if (this.time && !this.date) {
        this.control.type = "time";
    } else {
        this.control.type = "datetime";
    }
    d && (this.control.valueAsDate = d);
    this.control.onchange = this.field.onValueChange.bind(this.field);
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
    var d = value && new Date(value.year, (value.month - 1), value.day, value.hour, value.minute, 0);
    if (value) {
        ret.innerHTML = (this.date && (format_date(value) + " ") || "") + (this.time && format_time(value) || "");
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
    this.field = fld;
    this.time = false;
    this.date = true;
};

com.sweattrails.api.DateField.prototype = new com.sweattrails.api.DateTimeField();

/*
 * TimeField - Use DateTimeField, just without the date bits
 */

com.sweattrails.api.TimeField = function(fld, elem) {
    this.field = fld;
    this.time = true;
    this.date = false;
};

com.sweattrails.api.TimeField.prototype = new com.sweattrails.api.DateTimeField();

/*
 * FileField -
 */

com.sweattrails.api.FileField = function(fld, elem) {
    this.field = fld;
    this.multiple = elem.getAttribute("multiple") === "true";
};

com.sweattrails.api.FileField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input");
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "file";
    if (this.multiple) this.control.multiple = true;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    return this.control;
};

com.sweattrails.api.FileField.prototype.setValueFromControl = function(bridge, object) {
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
        this.submitParameter(elem.getAttribute("imageparameter") || "image",
            (function() {return this.control.files[0];}).bind(this));
        this.submitParameter(elem.getAttribute("contenttypeparameter") || "contentType",
            (function() {return this.control.files[0].type;}).bind(this));
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
com.sweattrails.api.internal.fieldtypes.title = com.sweattrails.api.TitleField;
com.sweattrails.api.internal.fieldtypes.text = com.sweattrails.api.TextField;
com.sweattrails.api.internal.fieldtypes.password = com.sweattrails.api.PasswordField;
com.sweattrails.api.internal.fieldtypes.weight = com.sweattrails.api.WeightField;
com.sweattrails.api.internal.fieldtypes.length = com.sweattrails.api.LengthField;
com.sweattrails.api.internal.fieldtypes.checkbox = com.sweattrails.api.CheckBoxField;
com.sweattrails.api.internal.fieldtypes.date = com.sweattrails.api.DateField;
com.sweattrails.api.internal.fieldtypes.datetime = com.sweattrails.api.DateTimeField;
com.sweattrails.api.internal.fieldtypes.time = com.sweattrails.api.TimeField;
com.sweattrails.api.internal.fieldtypes.file = com.sweattrails.api.FileField;
com.sweattrails.api.internal.fieldtypes.icon = com.sweattrails.api.IconField;
com.sweattrails.api.internal.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
com.sweattrails.api.internal.fieldtypes.lookup = com.sweattrails.api.LookupField;
com.sweattrails.api.internal.fieldtypes.choice = com.sweattrails.api.LookupField;

