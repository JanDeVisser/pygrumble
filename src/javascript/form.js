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
    this.id = id
    this.type = "form"
    if (container != null) {
        this.setContainer(container)
    }
    if (ds != null) {
        this.setDataSource(ds)
    }
    if (popup) {
        this.makePopup()
    }
    this.fields = []
    this.$ = {}
    this.footer = new com.sweattrails.api.ActionContainer(this, "footer")
    this.header = new com.sweattrails.api.ActionContainer(this, "header")
    this.mode = com.sweattrails.api.MODE_VIEW
    com.sweattrails.api.STManager.register(this)
    return this
}

com.sweattrails.api.Form.prototype.setContainer = function(c) {
    if (typeof(c) == "string") {
    	this.container = document.getElementById(this.id)
    } else {
    	this.container = c
    }
    this.table = null
}

com.sweattrails.api.Form.prototype.makePopup = function() {
    var container = document.createElement("div")
    container.id = this.id + "-popup"
    container.className = this.className || "popup"
    container.hidden = true
    this.container.appendChild(container)
    this.container = container
}

com.sweattrails.api.Form.prototype.makeModal = function() {
	var body = document.getElementsByTagName("body")[0]
    this.overlay = document.getElementById("overlay")
    if (!this.overlay) {
    	this.overlay = document.createElement("div")
        this.overlay.id = "overlay"
        this.overlay.className = "overlay"
        this.overlay.hidden = true
        body.appendChild(this.overlay)
    }
    var container = document.createElement("div")
    container.id = this.id + "-modal"
    container.className = "modal"
    container.hidden = true
    body.appendChild(container)
    this.container = container
    this.modal = true
}

com.sweattrails.api.Form.prototype.setTable = function(tableid) {
    this.id = tableid
    this.table = document.getElementById(this.id)
    this.container = null
}

com.sweattrails.api.Form.prototype.setDataSource = function(ds) {
    this.datasource = ds
    ds.addView(this)
}

com.sweattrails.api.Form.prototype.addField = function(fld) {
    this.fields.push(fld)
    fld.form = this
    this.$[fld.id] = fld
}

com.sweattrails.api.Form.prototype.addAction = function(action) {
    this.actions.add(action)
}

com.sweattrails.api.Form.field = function(fld) {
    for (var fix in this.fields) {
        var f = this.fields[fix]
        if (f.id == fld) return f
    }
    return null
}

com.sweattrails.api.Form.prototype.newTR = function() {
    if (!this.table) {
        this.table = document.createElement("table")
        this.table.width = "100%"
        p = (this.form) ? this.form : this.container
        p.appendChild(this.table)
    }
    var tr = document.createElement("tr")
    this.table.appendChild(tr)
    return tr
}

com.sweattrails.api.Form.prototype.render = function() {
    console.log("Form[" + this.id + "].render() " + this.container.className)
    if (!this.container || !this.container.hidden || (this.container.className == "tabpage")) {
        console.log("Container visible")
        if ((arguments.length > 0) && arguments[0]) {
            this.mode = arguments[0]
        } else if (this.init_mode) {
            this.mode = this.init_mode
            this.init_mode = null
        } else {
            this.mode = com.sweattrails.api.MODE_VIEW
        }
        var obj = null
        if (this.mode != com.sweattrails.api.MODE_NEW) {
            this.datasource.execute()
        } else {
            if (typeof(this.initialize) == "function") {
                obj = this.initialize()
            }
            this.datasource.setObject(obj)
            this.renderData(this.datasource.object)
        }
    }
}


com.sweattrails.api.Form.prototype.renderData = function(obj) {
    this.header.erase()
    this.footer.erase()
    if (this.form) {
    	this.container.removeChild(this.form)
    	this.form = null
    	this.table = null
    }
    if (this.table) {
        this.container.removeChild(this.table)
        this.table = null
    }
    this.header.render()
    this.renderedFields = []
    if (this.type == "form") {
        this.form = document.createElement("form")
        this.form.name = "form-" + this.id
        this.form.method = this.method
        this.form.action = this.action
        this.container.appendChild(this.form)    	
    }
    for (var ix in this.fields) {
    	var f = this.fields[ix]
        f.element = null
        if (f.render(this.mode, obj)) {
            this.renderedFields.push(f)
        }
    }
    this.footer.render()
}

com.sweattrails.api.Form.prototype.applyData = function() {
    if (this.mode != com.sweattrails.api.MODE_NEW) {
        this.datasource.reset()
        this.datasource.next()
    }
    for (fix in this.renderedFields) {
        f = this.renderedFields[fix]
        if (!f.readonly) {
            f.setValue(this.datasource.object)
        }
    }
    if (typeof(this.prepare) === "function") {
        this.prepare(this.datasource.object);
    }
}

com.sweattrails.api.Form.prototype.submit = function() {
    this.errors = [];
    if (this.validator != null) {
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
        this.progress("Saving ...");
        console.log("Submitting form " + this.id);
        if (this.form) {
            this.form.submit();
        } else {
            this.datasource.submit();
        }
    }
;}

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
    this.type = "builder"
    this.name = "formbuilder"
    com.sweattrails.api.STManager.processor("form", this)
}

com.sweattrails.api.FormBuilder.prototype.process = function(f) {
    var id = f.getAttribute("name")
    console.log("formBuilder: found form " + id)
    var ds = com.sweattrails.api.dataSourceBuilder.build(f)
    var form = new com.sweattrails.api.Form(id, f.parentNode, ds)
    this.buildForm(form, f)
}

com.sweattrails.api.FormBuilder.prototype.buildForm = function(form, elem) {
    form.type = 'json'
    if (elem.getAttribute("type")) {
        form.type = elem.getAttribute("type")
        if ("json;form".indexOf(form.type) < 0) {
            console.log("Invalid form type " + form.type + " for form " + form.id)
            form.type = "json"
        }
        if (form.type == "form") {
            form.action = elem.getAttribute("action")
            if (!form.action) {
                console.log("Missing form action for form " + form.id)
                form.type = "json"
            }
            form.method = "POST"
            if (elem.getAttribute("method")) {
                form.method = elem.getAttribute("method")
            }
        }
    }
    if (elem.getAttribute("mode")) {
        form.init_mode = elem.getAttribute("mode")
    }
    if (elem.getAttribute("initialize")) {
        form.initialize = getfunc(elem.getAttribute("initialize"))
    }
    if (elem.getAttribute("onsubmitted")) {
        form.onsubmitted = getfunc(elem.getAttribute("onsubmitted"))
    }
    if (elem.getAttribute("validate")) {
        this.validator = getfunc(elem.getAttribute("validate"))
    }
    if (elem.getAttribute("onerror")) {
        form.onerror = getfunc(elem.getAttribute("onerror"))
    }
    if (elem.getAttribute("onredirect")) {
        form.onredirect = getfunc(elem.getAttribute("onredirect"))
    }
    if (elem.getAttribute("class")) {
    	form.className = elem.getAttribute("class")
    }
    if (elem.getAttribute("popup") && ("true" == elem.getAttribute("popup"))) {
        form.makePopup()
    } else if (elem.getAttribute("modal") && ("true" == elem.getAttribute("modal"))) {
        form.makeModal()
    }
    var fields = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "field")
    for (var j = 0; j < fields.length; j++) {
        new com.sweattrails.api.FormField(form, fields[j])
    }
    form.footer.build(elem)
    var footer = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "footer")
    if (footer.length == 1) {
        form.footer.build(footer[0])
    }
    var header = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "header")
    if (header.length == 1) {
        form.header.build(header[0])
    }
}

new com.sweattrails.api.FormBuilder()

/**
 * FormField - Abstract base class for form elements
 */

com.sweattrails.api.internal.fieldtypes = {}

com.sweattrails.api.FormField = function(form, f) {
    this.hidden = false
    if (f) {
        this.type = "formfield"
	this.id = f.getAttribute("id") || f.getAttribute("property")
	$$.register(this)
	this.modes = f.getAttribute("mode")
	this.readonly = f.getAttribute("readonly") == "true"
	this.bridge = new com.sweattrails.api.internal.DataBridge()
	var p = f.getAttribute("property")
	if (p) {
	    this.bridge.get = p
	} else if (f.getAttribute("get")) {
	    this.bridge.get = getfunc(f.getAttribute("get"))
	    this.bridge.set = f.getAttribute("set") && getfunc(s)
	} else {
	    this.bridge.get = this.id
	}
	var onchange = f.getAttribute("onchange")
	if (onchange) {
	    this.onchange = getfunc(onchange)
	}
	if (f.getAttribute("validate")) {
	    this.validator = getfunc(f.getAttribute("validate"))
	}
	this.label = f.getAttribute("label")
	this.required = f.getAttribute("required") == "true"
	this.setType(f.getAttribute("type"), f)
	if (f.getAttribute("value")) {
            var v = f.getAttribute("value")
            this.defval = getfunc(v) || v
        }
    }
    form.addField(this)
    return this
}

com.sweattrails.api.FormField.prototype.setType = function(type, elem) {
    type = type || "text"
    var factory = com.sweattrails.api.internal.fieldtypes[type] || com.sweattrails.api.internal.fieldtypes.text
    $$.log(this, "typeof: " + type)
    this.impl = new factory(this, elem)
    this.impl.field = this
}

com.sweattrails.api.FormField.prototype.render = function(mode, object) {
    if (this.modes && (this.modes.length > 0) && (this.modes.indexOf(mode) < 0)) {
	return false
    }
    this.mode = mode
    var val = this.getValue(object)
    var elem = null
    if ((this.mode != com.sweattrails.api.MODE_VIEW) && !this.readonly) {
        elem = this.impl.renderEdit(val)
    } else if ((this.mode == com.sweattrails.api.MODE_VIEW) || this.readonly) {
        elem = this.impl.renderView(val)
    }
    if (this.parent) {
        if (this.element) {
            this.parent.removeChild(this.element)
        }
        this.element = elem
        this.parent.appendChild(this.element)
    } else {
        if (this.element && this.form.table) {
            this.form.table.removeChild(this.element)
        }
        var tr = null
        var td = null
        if (this.errors) {
            tr = this.form.newTR()        	
            td = document.createElement("td")
            td.colspan = 2
        	td.className = "validationerrors"
            tr.appendChild(td)
            var ul = document.createElement("ul")
            ul.appendChild(td)
            for (eix in this.errors) {
            	var li = document.createElement("li")
            	li.className = "validationerror"
            	li.innerHTML = this.errors[eix].message
            	ul.appendChild(li)
            }
        }
        tr = this.form.newTR()
        var lbl = this.label || this.id
        if (lbl) {
            lbl = (this.required) ? "(*) " + lbl + ":" : lbl + ":"
            td = document.createElement("td")
            td.style.textAlign = "right"
            td.width = this.width || "auto"
            var label = document.createElement("label")
            label.htmlFor = this.id
            label.innerHTML = lbl
            td.appendChild(label)
            tr.appendChild(td)
        }
        td = document.createElement("td")
        td.style.textAlign = "left"
        if (!lbl) {
            td.colspan = 2
        }
        td.appendChild(elem)
        tr.appendChild(td)
        this.element = tr
        this.element.id = this.id + "-fld-container"
    }
    this.element.hidden = this.hidden
    return true
}

Object.defineProperty(com.sweattrails.api.FormField.prototype, "hidden", {
    get: function() { return this._hidden },
    set: function(h) {
        this._hidden = h
        if (this.element) this.element.hidden = h
    }
})

com.sweattrails.api.FormField.prototype.validate = function() {
    this.errors = null
    if (this.impl.validator != null) {
    	ST_int.buildErrors(this, this.impl.validator())
    }
    if (this.validator != null) {
        ST_int.buildErrors(this, this.validator())
    }
    return this.errors
}

com.sweattrails.api.FormField.prototype.onValueChange = function() {
    if (this.onchange) {
        var val = this.impl.getValueFromControl()
        this.onchange(val)
    }
}

com.sweattrails.api.FormField.prototype.setValue = function(object) {
    this.bridge.setValue(object, this.impl.getValueFromControl())
}

com.sweattrails.api.FormField.prototype.getValue = function(object) {
    var ret = this.bridge.getValue(object)
    if (!ret && this.defval) {
        if (typeof(this.defval) == 'function') {
            ret = this.defval(object)
        } else {
            ret = this.defval
        }
    }
    return ret
}

/**
 * TextField -
 */

com.sweattrails.api.TextField = function(fld, elem) {
    this.field = fld
    this.size = elem.getAttribute("size")
    this.maxlength = elem.getAttribute("maxlength")
}

com.sweattrails.api.TextField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input")
    this.control.value = value || ""
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "text"
    if (this.size) this.control.size = this.size
    if (this.maxlength) this.control.maxLength = this.maxlength
    this.control.onchange = this.field.onValueChange.bind(this.field)
    return this.control
}

com.sweattrails.api.TextField.prototype.getValueFromControl = function() {
    return this.control.value
}

com.sweattrails.api.TextField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    ret.innerHTML = value || ""
    return ret
}

/**
 * PasswordField -
 */

com.sweattrails.api.PasswordField = function(fld, elem) {
    this.field = fld
    this.confirm = elem.getAttribute("confirm") && (elem.getAttribute("confirm") == "true")
}

com.sweattrails.api.PasswordField.prototype.renderEdit = function(value) {
    this.div = document.createElement("div")
    this.control = document.createElement("input")
    this.control.value =  ""
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "password"
    if (this.size) this.control.size = this.size
    if (this.maxlength) this.control.maxLength = this.maxlength
    this.control.onchange = this.field.onValueChange.bind(this.field)
    this.div.appendChild(this.control)
    if (this.confirm) {
	this.check = document.createElement("input")
	this.check.value =  ""
	this.check.name = this.field.id + "-check"
	this.check.id = this.field.id + "-check"
	this.check.type = "password"
	this.div.appendChild(this.check)
    }
    return this.div
}

com.sweattrails.api.PasswordField.prototype.validate = function() {
    if (this.confirm && (this.control.value != this.check.value)) {
	return "Password values do not match"
    } else {
	return null
    }
}

com.sweattrails.api.PasswordField.prototype.getValueFromControl = function() {
    this.value = this.control.value
    return this.value
}

com.sweattrails.api.PasswordField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    ret.innerHTML = "*******"
    return ret
}

/**
 * WeightField -
 */

com.sweattrails.api.WeightField = function(fld, elem) {
    this.field = fld
}

com.sweattrails.api.WeightField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span")
    this.control = document.createElement("input")
    var w = null
    if (value)
        w = weight(parseFloat(value), native_unit, false)
    this.control.value = w || ""
    this.control.value = value || ""
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "text"
    this.control.maxLength = 6
    this.control.size = 4 // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field)
    this.span.appendChild(this.control)
    this.unitSelector = document.createElement("select")
    this.unitSelector.name = this.field.id + "-units"
    this.unitSelector.id = this.unitSelector.name
    var option = document.createElement("option")
    option.selected = native_unit == "m"
    option.value = "1.0"
    option.text = "kg"
    this.unitSelector.appendChild(option)
    option = document.createElement("option")
    option.selected = native_unit == "i"
    option.value = "2.20462262"
    option.text = "lbs"
    this.unitSelector.onchange = this.field.onValueChange.bind(this.field)
    this.unitSelector.appendChild(option)
    this.span.appendChild(this.unitSelector)
    return this.span
}

com.sweattrails.api.WeightField.prototype.getValueFromControl = function() {
    this.value = parseFloat(this.control.value) / parseFloat(this.unitSelector.value)
    return this.value
}

com.sweattrails.api.WeightField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    var w = null
    if (value)
        w = weight(parseFloat(value), native_unit, true)
    ret.innerHTML = w || ""
    return ret
}

/**
 * LengthField -
 */

com.sweattrails.api.LengthField = function(fld, elem) {
    this.field = fld
}

com.sweattrails.api.LengthField.prototype.renderEdit = function(value) {
    this.span = document.createElement("span")
    this.control = document.createElement("input")
    var l = null
    if (value)
        l = length(parseFloat(value), native_unit, false)
    this.control.value = l || ""
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "text"
    this.control.maxLength = 6
    this.control.size = 4 // WAG
    this.control.onchange = this.field.onValueChange.bind(this.field)
    this.span.appendChild(this.control)
    this.unitSelector = document.createElement("select")
    this.unitSelector.name = this.field.id + "-units"
    this.unitSelector.id = this.unitSelector.name
    var option = document.createElement("option")
    option.selected = native_unit == "m"
    option.value = "1.0"
    option.text = "cm"
    this.unitSelector.appendChild(option)
    option = document.createElement("option")
    option.selected = native_unit == "i"
    option.value = "0.393700787"
    option.text = "in"
    this.unitSelector.appendChild(option)
    this.unitSelector.onchange = this.field.onValueChange.bind(this.field)
    this.span.appendChild(this.unitSelector)
    return this.span
}

com.sweattrails.api.LengthField.prototype.getValueFromControl = function() {
    var v = this.control.value
    if (v) {
        v = v.trim()
        if ((this.unitSelector.value != 1.0) && (v.indexOf("'") > 0)) {
            var a = v.split("'")
            v = 12*parseInt(a[0].trim()) + parseInt(a[1].trim())
        } else {
            v = parseFloat(v)
        }
        this.value = v / parseFloat(this.unitSelector.value)
    } else {
        this.value = 0
    }
    return this.value
}

com.sweattrails.api.LengthField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    var l = null
    if (value)
        l = length(parseFloat(value), native_unit, true)
    ret.innerHTML = l || ""
    return ret
}

/**
 * LookupField -
 */

com.sweattrails.api.LookupField = function(fld, elem) {
    this.text = elem.getAttribute("text") || "value"
    this.key = elem.getAttribute("key") || "key"
    this.type = elem.getAttribute("presentationtype") || "dropdown"
    var projection = elem.getAttribute("projection") || "object"
    this.prj = getfunc(projection) ||
        ((projection == "property") && function(obj) { return obj[this.projectionProperty] }) ||
        function(obj) { return obj }
    this.projectionProperty = elem.getAttribute("projectionproperty") || this.key
    this.values = []
    this.valuesByKey = {}
    this.value = null
    this.field = fld
    this.ds = com.sweattrails.api.dataSourceBuilder.build(elem)
    this.ds.addView(this)
    this.ds.execute()
}

com.sweattrails.api.LookupField.prototype.onData = function() {
    this.values = []
    this.valuesByKey = {}
}

com.sweattrails.api.LookupField.prototype.renderData = function(obj) {
    this.values.push(obj)
    this.valuesByKey[obj[this.key]] = obj
}

com.sweattrails.api.LookupField.prototype.onDataEnd = function() {
    this.populateSelect()
    this.populateSpan()
}

com.sweattrails.api.LookupField.prototype.populateSelect = function() {
    if (this.control) {
	if (this.type == "dropdown") {
	    for (var ix = 0; ix < this.values.length; ix++) {
		var v = this.values[ix]
		var option = document.createElement("option")
		option.selected = (v[this.key] == (this.value && this.value[this.key]))
		option.value = v[this.key]
		option.text = v[this.text]
		this.control.appendChild(option)
	    }
	}
	if (this.type == "radio") {
	    this.radiobuttons = []
	    for (ix = 0; ix < this.values.length; ix++) {
		v = this.values[ix]
		var span = document.createElement("span")
		option = document.createElement("input")
		option.name = this.field.id
		option.checked = (v[this.key] == this.value[this.key])
		option.type = "radio"
		option.value = v[this.key]
		span.appendChild(option)
		var s = document.createElement("span")
		s.innerHTML = v.text
		span.appendChild(s)
		this.control.appendChild(span)
		this.radiobuttons.push(option)
	    }
	}
    }
}

com.sweattrails.api.LookupField.prototype.populateSpan = function() {
    if (this.span) {
	this.span.innerHTML = this.valuesByKey[this.value[this.key]][this.text]
    }
}

com.sweattrails.api.LookupField.prototype.renderEdit = function(value) {
    this.value = value
    if (this.type == "dropdown") {
	this.control = document.createElement("select")
	this.control.name = this.field.id
	this.control.id = this.field.id
	var option
	if (!this.field.required) {
	    option = document.createElement("option")
	    option.selected = !value
	    option.value = ""
	    option.text = ""
	    this.control.appendChild(option)
	}
    } else if (this.type == "radio") {
	this.control = document.createElement("span")
	this.control.id = this.field.id + "-radiospan"
    }
    this.populateSelect(this.value)
    this.control.onchange = this.field.onValueChange.bind(this.field)
    return this.control
}

com.sweattrails.api.LookupField.prototype._getValueForKey = function(key) {
    var obj = this.valuesByKey[key]
    this.value = this.prj(obj)
}

com.sweattrails.api.LookupField.prototype.getValueFromControl = function() {
    this.value = null
    if (this.type == "dropdown") {
        _getValueForKey(this.control.value)
    } else if (this.type == "radio") {
	for (ix = 0; ix < this.radiobuttons.length; ix++) {
	    var rb = this.radiobuttons[ix]
	    if (rb.checked) {
                _getValueForKey(rb.value)
	    }
	}
    }
    return this.value
}

com.sweattrails.api.LookupField.prototype.renderView = function(value) {
    this.value = value
    this.span = document.createElement("span")
    this.populateSpan()
    return this.span
}

/**
 * CheckBoxField -
 */

com.sweattrails.api.CheckBoxField = function(fld, elem) {
    this.field = fld
}

com.sweattrails.api.CheckBoxField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input")
    this.control.value = true
    this.control.checked = value
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "checkbox"
    this.control.onchange = this.field.onValueChange.bind(this.field)
    return this.control
}

com.sweattrails.api.CheckBoxField.prototype.getValueFromControl = function() {
    return this.control.checked
}

com.sweattrails.api.CheckBoxField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    if (value) {
	var img = document.createElement("img")
	img.src = "/images/checkmark.png"
	img.height = 24
	img.width = 24
	ret.appendChild(img)
    } else {
	ret.innerHTML = "&#160;"
    }
    return ret
}

/**
 * DateTimeField -
 */

com.sweattrails.api.DateTimeField = function(fld, elem) {
    this.field = fld
    this.date = this.time = true
}

com.sweattrails.api.DateTimeField.prototype.renderEdit = function(value) {
    var span = document.createElement("span")
    var d = value && new Date(value.year, (value.month - 1), value.day)
    if (this.date) {
        this.datecontrol = document.createElement("input")
        this.datecontrol.name = this.field.id + "-date"
        this.datecontrol.id = this.datecontrol.name
        this.datecontrol.type = "date"
        d && (this.datecontrol.valueAsDate = d)
        this.datecontrol.onchange = this.field.onValueChange.bind(this.field)
        span.appendChild(this.datecontrol)
    }

    if (this.time) {
        this.hrcontrol = document.createElement("select")
        this.hrcontrol.name = this.field.id + "-hour"
        this.hrcontrol.id = this.hrcontrol.name
        for (var h = 0; h < 24; h++) {
            var option = document.createElement("option")
            option.selected = value && (value.hour == h)
            option.value = h
            option.text = h
            this.hrcontrol.appendChild(option)
        }
        this.hrcontrol.onchange = this.field.onValueChange.bind(this.field)
        span.appendChild(this.hrcontrol)

        this.mincontrol = document.createElement("select")
        this.mincontrol.name = this.field.id + "-min"
        this.mincontrol.id = this.mincontrol.name
        for (var m = 0; m < 24; m++) {
            option = document.createElement("option")
            option.selected = value && (value.minute == m)
            option.value = m
            option.text = m
            this.mincontrol.appendChild(option)
        }
        this.mincontrol.onchange = this.field.onValueChange.bind(this.field)
        span.appendChild(this.mincontrol)
    }

    return span
}

com.sweattrails.api.DateTimeField.prototype.getValueFromControl = function() {
    var ret = {}
    if (this.date) {
        var v = this.datecontrol.valueAsDate
        if (v) {
            ret.year = v.getFullYear()
            ret.month = v.getUTCMonth() + 1
            ret.day = v.getUTCDate()
        }
    }
    if (this.time) {
        console.log("---> " + this.hrcontrol.value)
        ret.hour = parseInt(this.hrcontrol.value, 10)
        ret.minute = parseInt(this.mincontrol.value, 10)
    }
    return ret
}

com.sweattrails.api.DateTimeField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    var d = value && new Date(value.year, (value.month - 1), value.day, value.hour, value.minute, 0)
    if (value) {
        ret.innerHTML = (this.date && (format_date(value) + " ") || "") + (this.time && format_time(value) || "")
    } else {
        ret.innerHTML = "&#160;"
    }
    return ret
}

/**
 * DateField - Use DateTimeField, just without the time bits
 */

com.sweattrails.api.DateField = function(fld, elem) {
    this.field = fld
    this.time = false
    this.date = true
}

com.sweattrails.api.DateField.prototype = new com.sweattrails.api.DateTimeField()

/**
 * TimeField - Use DateTimeField, just without the date bits
 */

com.sweattrails.api.TimeField = function(fld, elem) {
    this.field = fld
    this.time = true
    this.date = false
}

com.sweattrails.api.TimeField.prototype = new com.sweattrails.api.DateTimeField()

/**
 * FileField -
 */

com.sweattrails.api.FileField = function(fld, elem) {
    this.field = fld
    this.multiple = elem.getAttribute("multiple") == "true"
}

com.sweattrails.api.FileField.prototype.renderEdit = function(value) {
    this.control = document.createElement("input")
    this.control.name = this.field.id
    this.control.id = this.field.id
    this.control.type = "file"
    if (this.multiple) this.control.multiple = true
    this.control.onchange = this.field.onValueChange.bind(this.field)
    return this.control
}

com.sweattrails.api.FileField.prototype.getValueFromControl = function() {
    return (this.multiple) ? this.control.files : this.control.files[0]
}

com.sweattrails.api.FileField.prototype.renderView = function(value) {
    var ret = document.createElement("span")
    ret.innerHTML = "<i>... File ...</i>"
    return ret
}

/**
 * IconField -
 */

com.sweattrails.api.IconField = function(fld, elem) {
    this.field = fld
    this.height = elem.getAttribute("height") || 48
    this.width = elem.getAttribute("width") || 48
    this.datasource = com.sweattrails.api.dataSourceBuilder.build(elem)
    if (this.datasource) {
        this.submitParameter(elem.getAttribute("imageparameter") || "image",
            (function() {return this.control.files[0]}).bind(this))
        this.submitParameter(elem.getAttribute("contenttypeparameter") || "contentType",
            (function() {return this.control.files[0].type}).bind(this))
        this.datasource.submitAsJSON = false
        this.datasource.addView(this)
    }
    fld.readonly = true
}

com.sweattrails.api.IconField.prototype.renderEdit = function(value) {
    return null
}

com.sweattrails.api.IconField.prototype.getValueFromControl = function() {
    return null
}

com.sweattrails.api.IconField.prototype.renderView = function(value) {
    var div = document.createElement("div")
    if (this.url && (this.field.mode == com.sweattrails.api.MODE_VIEW)) {
        var onDragEnter = function() {
            this.entered++;
            this.control.style.display='block'
        }
        var onDragLeave = function() {
            this.entered--;
            if (!this.entered) this.control.style.display='none'
        }
        div.ondragenter = onDragEnter.bind(this)
        div.ondragleave = onDragLeave.bind(this)
    }

    var img = document.createElement("img")
    img.src = value
    img.height = this.height
    img.width = this.width
    div.appendChild(img)

    if (this.datasource && (this.field.mode == com.sweattrails.api.MODE_VIEW)) {
        this.control = document.createElement("input")
        this.control.name = this.field.id
        this.control.id = this.field.id
        this.control.type = "file"
        this.control.style.display = "none"
        this.control.style.position = "absolute"
        this.control.style.top = this.control.style.left = this.control.style.right = this.control.style.bottom = 0
        this.control.style.opacity = 0

        var submitFnc = function() {
            this.datasource.createObjectFrom(this.field.form.datasource.getObject())
            this.datasource.submit()
        }
        this.control.onchange = submitFnc.bind(this)
        div.appendChild(this.control)
    }
    return div
}

com.sweattrails.api.IconField.prototype.onDataSubmitted = function() {
    this.field.form.render()
}

com.sweattrails.api.IconField.prototype.onDataError = function() {
    this.field.form.render()
}

com.sweattrails.api.internal.fieldtypes.text = com.sweattrails.api.TextField
com.sweattrails.api.internal.fieldtypes.password = com.sweattrails.api.PasswordField
com.sweattrails.api.internal.fieldtypes.weight = com.sweattrails.api.WeightField
com.sweattrails.api.internal.fieldtypes.length = com.sweattrails.api.LengthField
com.sweattrails.api.internal.fieldtypes.checkbox = com.sweattrails.api.CheckBoxField
com.sweattrails.api.internal.fieldtypes.date = com.sweattrails.api.DateField
com.sweattrails.api.internal.fieldtypes.datetime = com.sweattrails.api.DateTimeField
com.sweattrails.api.internal.fieldtypes.time = com.sweattrails.api.TimeField
com.sweattrails.api.internal.fieldtypes.file = com.sweattrails.api.FileField
com.sweattrails.api.internal.fieldtypes.icon = com.sweattrails.api.IconField
com.sweattrails.api.internal.fieldtypes.lookup = com.sweattrails.api.LookupField
com.sweattrails.api.internal.fieldtypes.choice = com.sweattrails.api.LookupField
