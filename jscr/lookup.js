/*
 * Copyright (c) 2014-2018 Jan de Visser (jan@sweattrails.com)
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


 /**
 * LookupField - A formfield providing allowing the user to select a value from
 * a lookup datasource.
 *
 * @param {type} fld The FormField object this field implementation is
 * associated with.
 * @param {type} elem The document node defining the field.
 * @returns A new LookupField field implementation object.
 */
com.sweattrails.api.internal.LookupField = class extends __.FormField {
    constructor(form, elem, parent, options) {
        super(form, elem, parent, options);
        this.text = options.text || "value";
        this.key = options.key || "key";
        this.icon = options.icon || null;
        this.type = options.presentationtype || "select";

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
        this.values = [];
        this.valuesByKey = {};
        this.ds = __.dataSourceBuilder.build(elem);
        this.ds.addView(this);
        this.ds.execute();
    };

    renderData(obj) {
        const v = {key: obj[this.key], text: obj[this.text], object: obj};
        if (this.icon) {
            v.icon = obj[this.icon];
        }
        this.values.push(obj);
        this.valuesByKey[v.key] = v;
    };

    view() {
        if (this.span) {
            if (this.value && (this.value in this.valuesByKey)) {
                const obj = this.valuesByKey[this.value];
                if (obj.icon) {
                    var img = document.createElement("img");
                    img.src = obj.icon;
                    img.width = img.height = 24;
                    this.span.appendChild(img);
                }
                this.span.appendChild(document.createTextNode(obj.text));
            }
        }
    };

    setControl(control) {
        this.control = control;
        this.control.name = this.id;
        this.control.id = this.id;
        this.control.onchange = this.onValueChange.bind(this);
        return this.control;
    };

    _getValueForKey(key) {
        this.value = this.prj(this.valuesByKey[key]);
    };

    setValueFromControl(bridge, object) {
        this.value = this.impl.getValue();
        bridge.setValue(object, this.value);
    };

    renderView(value) {
        this.value = value;
        this.span = document.createElement("span");
        this.view();
        return this.span;
    };

    clear() {
        this.setValue("");
    };
};

com.sweattrails.api.internal.lookup = {};

/**
 * Lookup type Select -
 */
com.sweattrails.api.internal.lookup.Select = class extends ST_int.LookupField {
    constructor(form, elem, parent, options) {
        super(form, elem, parent, options);
    };

    renderEdit(value) {
        this.control = document.createElement("select");
        if (!this.required) {
            const option = document.createElement("option");
            option.value = "";
            option.text = "";
            this.control.appendChild(option);
        }
        this.values.forEach((obj, ix) => {
            const option = document.createElement("option");
            option.value = obj.key;
            option.text = obj.text;
            option.selected = (option.value === value);
            this.control.appendChild(option);
        });
        return this.control;
    };

    _setValue(value) {
        Array.from(this.control.options).forEach((option, ix) => {
            if (option.value === value) {
                this.control.selectedIndex = ix;
            }
        });
    };

    _getValue() {
        return this.control.value;
    };
};

/*
 * Lookup type Radio -
 */
com.sweattrails.api.internal.lookup.Radio = class extends ST_int.LookupField {
    constructor(form, elem, parent, options) {
        super(form, elem, parent, options);
    };

    renderEdit(value) {
        this.radiobuttons = [];
        this.control = document.createElement("span");
        this.values.forEach((obj) => {
            const span = document.createElement("span");
            const option = document.createElement("input");
            option.type = "radio";
            option.name = this.getElementID();
            option.value = obj.key;
            if (option.value === value) {
                option.defaultChecked = true;
            }
            this.radiobuttons.push(option);
            span.appendChild(option);
            const s = document.createElement("span");
            s.innerHTML = obj.text;
            span.appendChild(s);
            this.control.appendChild(span);
        });
        return this.control;
    };

    _getValue() {
        return this.radiobuttons.reduce((value, rb) => {
            return value || (rb.checked && rb.value);
        }, null);
    };

    _setValue(value) {
        return this.radiobuttons.forEach((rb) => {
            if (rb.value === value) {
                rb.checked = true;
            }
        });
    };
};

/*
 * Lookup type DataList -
 */

com.sweattrails.api.internal.lookup.DataList = class extends ST_int.LookupField {
    constructor(form, elem, parent, options) {
        super(form, elem, parent, options);
    };

    renderEdit(value) {
        this.control = com.sweattrails.api.internal.buildInput("text", value);
        return this.control;
    };

    _setValue(value) {
        this.control.value = value;
    }

    _getValue() {
        return this.control.value;
    };
}

com.sweattrails.api.internal.lookuptype = {
    select:   com.sweattrails.api.internal.lookup.Select,
    radio:    com.sweattrails.api.internal.lookup.Radio,
    datalist: com.sweattrails.api.internal.lookup.DataList
};

com.sweattrails.api.LookupFieldFactory = function(form, elem, parent, options) {
    const type = options.presentationtype || "select";
    const cls = com.sweattrails.api.internal.lookuptype[type]
       || com.sweattrails.api.internal.lookup.Select;
    return new cls(form, elem, parent, options);
};

ST_int.fieldtypes.lookup = ST.LookupFieldFactory;
ST_int.fieldtypes.choice = ST.LookupFieldFactory;
