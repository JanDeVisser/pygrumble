/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */


com.sweattrails.api.LookupField = function(fld, elem) {
    this.text = elem.getAttribute("text") || "value"
    this.key = elem.getAttribute("key") || "key"
    this.icon = elem.getAttribute("icon") || null
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
    console.log("push " + obj[this.key] + ": " + obj[this.text])
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
		s.innerHTML = v[this.text]
		span.appendChild(s)
		this.control.appendChild(span)
		this.radiobuttons.push(option)
	    }
	}
    }
}

com.sweattrails.api.LookupField.prototype.populateSpan = function() {
    if (this.span) {
        if (this.icon) {
            var img = document.createElement("img")
            img.src = value[this.icon]
            img.width = img.height = 24
            this.span.appendChild(img)
        }
        var txt = document.createTextNode()
	txt.innerHTML = value[this.text]
        this.span.appendChild(txt)
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
        this._getValueForKey(this.control.value)
    } else if (this.type == "radio") {
	for (ix = 0; ix < this.radiobuttons.length; ix++) {
	    var rb = this.radiobuttons[ix]
	    if (rb.checked) {
                this._getValueForKey(rb.value)
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

com.sweattrails.api.internal.fieldtypes.lookup = com.sweattrails.api.LookupField
