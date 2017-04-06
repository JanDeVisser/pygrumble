/**
 * LookupField - A formfield providing allowing the user to select a value from
 * a lookup datasource.
 * 
 * @param {type} fld The FormField object this field implementation is 
 * associated with.
 * @param {type} elem The document node defining the field.
 * @returns A new LookupField field implementation object.
 */
com.sweattrails.api.LookupField = function(fld, elem) {
    this.text = elem.getAttribute("text") || "value";
    this.key = elem.getAttribute("key") || "key";
    this.icon = elem.getAttribute("icon") || null;
    this.type = elem.getAttribute("presentationtype") || "select";
    
    /* Projection - need to define */
    /*
    var projection = elem.getAttribute("projection") || "object";
    this.prj = __.getfunc(projection) ||
        ((projection === "property") && function(obj) { return obj[this.projectionProperty]; }) ||
        function(obj) { return obj; };
    this.projectionProperty = elem.getAttribute("projectionproperty") || this.key;
    */
    this.value = null;
    this.field = fld;
    var impl = com.sweattrails.api.internal.lookuptype[this.type];
    this.impl = impl(this, elem);
    this.ds = com.sweattrails.api.dataSourceBuilder.build(elem);
    this.ds.addView(impl);
    this.ds.execute();
};

com.sweattrails.api.LookupField.prototype.view = function() {
    if (this.span) {
        if (this.icon) {
            var img = document.createElement("img");
            img.src = value[this.icon];
            img.width = img.height = 24;
            this.span.appendChild(img);
        }
        if (this.value && (this.value in this.valuesByKey)) {
            var obj = this.valuesByKey[this.value];
            var txt = obj[this.text];
            this.span.innerHTML = txt;
        }
    }
};

com.sweattrails.api.LookupField.prototype.renderEdit = function(value) {
    this.value = value;
    this.impl.renderEdit();
};

com.sweattrails.api.LookupField.prototype.setControl = function(control) {
    this.control = control;
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    return this.control;
};

com.sweattrails.api.LookupField.prototype._getValueForKey = function(key) {
    var obj = this.valuesByKey[key];
    this.value = this.prj(obj);
};

com.sweattrails.api.LookupField.prototype.setValueFromControl = function(bridge, object) {
    this.value = this.impl.getValue();
    bridge.setValue(object, this.value);
};

com.sweattrails.api.LookupField.prototype.renderView = function(value) {
    this.value = value;
    this.span = document.createElement("span");
    this.view();
    return this.span;
};

com.sweattrails.api.LookupField.prototype.clear = function() {
    this.setValue("");
};

com.sweattrails.api.LookupField.prototype.setValue = function(value) {
    this.value = value;
    this.impl.setValue();
};

com.sweattrails.api.internal.fieldtypes.lookup = com.sweattrails.api.LookupField;

com.sweattrails.api.internal.lookup = {};


/*
 * Lookup type Select -
 */

com.sweattrails.api.internal.lookup.Select = function(lookup, elem) {
    this.lookup = lookup;
};

com.sweattrails.api.internal.lookup.Select.prototype.renderEdit = function(obj) {
    this.lookup.ds.execute();
};

com.sweattrails.api.internal.lookup.Select.prototype.onData = function() {
    if (!this.control) {
        this.control = document.createElement("select");
        var option;
        if (!this.lookup.field.required) {
            option = document.createElement("option");
            option.selected = !value;
            option.value = "";
            option.text = "";
            this.control.appendChild(option);
        }
        this.lookup.setControl(this.control);
    }
};

com.sweattrails.api.internal.lookup.Select.prototype.renderData = function(obj) {
    option = document.createElement("option");
    option.selected = (obj[this.lookup.key] === this.lookup.value);
    option.value = obj[this.lookup.key];
    option.text = obj[this.lookup.text];
    this.control.appendChild(option);
};

com.sweattrails.api.internal.lookup.Select.prototype.setValue = function() {
    var value = this.control.value;
    for (var ix = 0; ix < this.control.length; ix++) {
        var option = this.control.options[ix];
        if (option.value === value) {
            this.control.selectedIndex = ix;
            return;
        }
    }
};

com.sweattrails.api.internal.lookup.Select.prototype.getValue = function() {
    return this.control.value;
};

/*
 * Lookup type Radio -
 */

com.sweattrails.api.internal.lookup.Radio = function(lookup, elem) {
    this.lookup = lookup;
};

com.sweattrails.api.internal.lookup.Radio.prototype.renderEdit = function(obj) {
    this.lookup.ds.execute();
};

com.sweattrails.api.internal.lookup.Radio.prototype.onData = function() {
    if (!this.control) {
        this.radiobuttons = [];
        this.control = document.createElement("span");
        this.lookup.setControl(this.control);
    }
};

com.sweattrails.api.internal.lookup.Radio.prototype.renderData = function(obj) {
    var span = document.createElement("span");
    var option = document.createElement("input");
    option.name = this.lookup.field.id;
    option.defaultChecked = (obj[this.lookup.key] === this.lookup.value);
    option.type = "radio";
    option.value = obj[this.lookup.key];
    span.appendChild(option);
    var s = document.createElement("span");
    s.innerHTML = obj[this.lookup.text];
    span.appendChild(s);
    this.control.appendChild(span);
    this.radiobuttons.push(option);
};

com.sweattrails.api.internal.lookup.Radio.prototype.getValue = function() {
    for (ix = 0; ix < this.radiobuttons.length; ix++) {
        var rb = this.radiobuttons[ix];
        if (rb.checked) {
            return rb.value;
        }
    }
    return null;
};

com.sweattrails.api.internal.lookup.Radio.prototype.setValue = function() {
    var value = this.control.value;
    for (ix = 0; ix < this.radiobuttons.length; ix++) {
        var rb = this.radiobuttons[ix];
        if (rb.value === value) {
            rb.checked = true;
            return;
        }
    }
};

/*
 * Lookup type DataList -
 */

com.sweattrails.api.internal.lookup.DataList = function(lookup, elem) {
    this.lookup = lookup;
    this.elem = elem;
};

com.sweattrails.api.internal.lookup.DataList.prototype.renderEdit = function() {
    this.control = com.sweattrails.api.internal.buildInput("text", this.lookup.field.id, this.lookup.elem, this.lookup.value);
    this.lookup.setControl(this.control);
};

com.sweattrails.api.internal.lookup.DataList.prototype.getValue = function() {
    return this.control.value;
};

com.sweattrails.api.internal.lookuptype = {
    select:   com.sweattrails.api.internal.lookup.Select,
    radio:    com.sweattrails.api.internal.lookup.Radio,
    datalist: com.sweattrails.api.internal.lookup.DataList
};

