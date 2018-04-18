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
 * Form -
 */

com.sweattrails.api.formmodes = {
    VIEW: "view",
    EDIT: "edit",
    NEW: "new",
    ERROR: "error",
};

com.sweattrails.api.internal.fieldtypes = {};

com.sweattrails.api.show_form = function(id, mode = com.sweattrails.api.formmodes.NEW) {
    const form = $(id);
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

/* ----------------------------------------------------------------------- */

com.sweattrails.api.Form = class extends com.sweattrails.api.Component {
    constructor(container, options = {}) {
        super("form", container, options);
        this.table = null;
        this.form = null;
        this.box = null;
        this.fields = [];
        this.$ = {};
        this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
        this.header = new com.sweattrails.api.ActionContainer(this, "header");
        this.mode = com.sweattrails.api.formmodes.VIEW;
        if (options.type) {
            this.formtype = options.type.toLowerCase();
            if (["json", "form"].indexOf(this.formtype) < 0) {
                this.log(`Invalid form type ${this.formtype} for form ${this.id}`);
                this.formtype = "json";
            }
            if (this.formtype === "form") {
                this.action = options.action;
                if (!this.action) {
                    this.log(`Missing form action for form ${this.id}`);
                    this.formtype = "json";
                }
                this.method = "POST";
                if (options.method) {
                    this.method = options.method;
                }
            }
        }
        this.formtype = this.formtype || 'json';
        this.layout = options.layout || "table";
        this.submitMessage = options.submitmessage || "Saving ...";
        if (options.class) {
            this.className = options.class;
        }
        if (this.formtype === 'form') {
            this.form = document.createElement('form');
            this.form.name = "form-" + this.id;
            this.form.method = this.method;
            this.form.action = this.action;
            this.box = this.form;
        } else {
            this.box = document.createElement('div');
            this.box.id = 'form-' + this.id + '-fieldbox';
            this.box.className = 'form-fieldbox';
        }
        if (com.sweattrails.api.toBoolean(this.options.popup)) {
            this.element = this.makePopup();
        } else if (com.sweattrails.api.toBoolean(this.options.modal)) {
            this.element = this.makeModal();
        } else {
            this.element = this.box;
        }
    }

    build() {
        if (options.mode) {
            this.init_mode = options.mode;
        }
        if (options.initialize) {
            this.initialize = com.sweattrails.api.getfunc(options.initialize);
        }
        if (options.ondata) {
            this.ondata = com.sweattrails.api.getfunc(options.ondata);
        }
        if (options.onsubmitted) {
            this.onsubmitted = com.sweattrails.api.getfunc(options.onsubmitted);
        }
        if (options.onsuccess) {
            this.onsuccess = com.sweattrails.api.getfunc(options.onsuccess);
        }
        if (options.validate) {
            this.validator = com.sweattrails.api.getfunc(options.validate);
        }
        if (options.onerror) {
            this.onerror = com.sweattrails.api.getfunc(options.onerror);
        }
        if (options.onredirect) {
            this.onredirect = com.sweattrails.api.getfunc(options.onredirect);
        }
        if (options.afterdelete) {
            this.afterdelete = options.afterdelete;
        }
        if (options.kind) {
            this.buildFormForKind(options.kind);
        }
    };

    /* == Form construction ============================================== */

    hasDatasource() {
        return true;
    }

    buildFormForKind(kind) {
        this.schemads = new com.sweattrails.api.JSONDataSource("/schema/" + kind);
        this.schemads.async = false;
        this.schemads.this = this;
        this.schemads.renderData = function(obj) {
            obj.properties.forEach((p) => {
                const fld = com.sweattrails.api.createField(this, p);
            });
        };
        this.schemads.execute();
    };

    makePopup() {
        const popup = document.createElement("div");
        popup.id = this.id + "-popup";
        popup.className = this.className || "popup";
        popup.hidden = true;
        return popup;
    };

    makeModal() {
        this.overlay = document.getElementById("overlay");
        if (!this.overlay) {
            this.overlay = document.createElement("div");
            this.overlay.id = "overlay";
            this.overlay.className = "overlay";
            this.overlay.hidden = true;
            document.body.appendChild(this.overlay);
        }
        const modal = document.createElement("div");
        modal.id = this.id + "-modal";
        modal.className = "modal";
        modal.hidden = true;
        document.body.appendChild(modal);
        this.modal = true;
        return modal;
    };

    addField(field) {
        this.log(`Adding field ${field.id}`);
        this.fields.push(field);
        if (typeof(field.id) !== "undefined") {
            this.$[field.id] = field;
        }
    };

    addAction(action) {
        this.actions.add(action);
    };

    /* =================================================================== */

    field(fld) {
        return this.$[fld];
    };

    _(fld) {
        return (fld in this.$) ? this.$[fld].getValue() : null;
    };

    /* == Form rendering ================================================== */

    newTR() {
        if (!this.table) {
            this.table = document.createElement("table");
            this.table.width = "100%";
            this.box.appendChild(this.table);
        }
        const tr = document.createElement("tr");
        this.table.appendChild(tr);
        return tr;
    };

    render(mode) {
        this.log(`render() class: ${this.parent.className}`);
        if (!this.parent || !this.parent.hidden || (this.container.type === "tab")) {
            this.rebuild();
            if (mode) {
                if (mode !== com.sweattrails.api.formmodes.ERROR) {
                    this.mode = mode;
                }
            } else if (this.init_mode) {
                mode = this.mode = this.init_mode;
                this.init_mode = null;
            } else {
                mode = this.mode = com.sweattrails.api.formmodes.VIEW;
            }
            switch (mode) {
                case com.sweattrails.api.formmodes.VIEW:
                case com.sweattrails.api.formmodes.EDIT:
                    this.datasource.execute();
                    break;
                case com.sweattrails.api.formmodes.NEW:
                    const obj = (typeof(this.initialize) === "function") ? this.initialize() : null;
                    this.datasource.setObject(obj);
                    // Fall through
                case com.sweattrails.api.formmodes.ERROR:
                    this.renderData(this.datasource.getObject());
                    break;
            }
        }
    };

    renderData(obj) {
        com.sweattrails.api.dump(obj, "Rendering form with data -");
        this.fields.forEach((f) => {
            this.log(`rendering field ${f.id}`);
            if (f.render(this.mode, obj)) {
                this.renderedFields.push(f);
            }
        });
    };

    clear() {
        this.header.erase();
        this.footer.erase();
        if (this.renderedFields) {
            this.renderedFields.forEach((f) => {
                f.erase();
                if (f.element) {
                    (this.table || this.parent).removeChild(f.element);
                }
                f.element = null;
            });
            if (this.table) {
                this.box.removeChild(this.table);
                this.table = null;
            }
            $$.assert(this, !this.form || (this.form === this.box),
                "form's fieldbox not the same as its form")
            if (this.box) {
                this.parent.removeChild(this.box);
                this.form = this.box = null;
            }
        }
        this.renderedFields = [];
    };

    rebuild() {
        this.clear();
        this.header.render();
        this.footer.render();
    };

    applyData() {
        // FIXME: Why?
        // if (this.mode !== com.sweattrails.api.formmodes.NEW) {
        //     this.datasource.reset();
        //     this.datasource.next();
        // }
        const obj = this.datasource.getObject();
        this.renderedFields.forEach(function(f) {
            if (!f.readonly) {
                f.assignValueToObject(obj);
            }
        });
        if (typeof(this.prepare) === "function") {
            this.prepare(obj);
        }
        com.sweattrails.api.dump(obj, `${this}.applyData`);
    };

    submit() {
        this.errors = [];
        if (this.validator) {
            ST_int.buildErrors(this, this.validator());
        }
        this.renderedFields.forEach((f) => {
            f.errors = f.validate();
            if (f.errors) {
                this.errors = this.errors.concat(f.errors);
            }
        });
        this.applyData();
        if (this.errors.length > 0) {
            this.render(com.sweattrails.api.formmodes.ERROR);
        } else {
            this.progress(this.submitMessage);
            this.log("Submitting form...");
            if (this.form) {
                this.form.submit();
            } else {
                this.datasource.submit();
            }
        }
    };

    delete() {
        const mth = this.datasource.method || undefined;
        const redir = this.datasource.getParameter("redirect");
        this.datasource.method = "DELETE";
        this.datasource.parameter("redirect", this.afterdelete || "/");
        this.datasource.execute();
        mth && (this.datasource.method = mth);
        if (redir) {
            this.datasource.parameter("redirect", redir);
        } else {
            this.datasource.delParameter("redirect");
        }
    };

    progressOff() {
        this.footer.progressOff();
    };

    progress(msg) {
        this.footer.progress(msg);
    };

    error(msg) {
        this.footer.error && this.footer.error(msg);
    };

    popup(mode) {
        if (this.modal) {
            document.getElementById("overlay").hidden = false;
        }
        this.parent.hidden = false;
        this.ispopup = true;
        this.render(mode);
    };

    close() {
        try {
            this.progressOff();
            if (this.ispopup) {
                this.parent.hidden = true;
                if (this.modal) {
                    this.overlay.hidden = true;
                }
            } else {
                if (this.mode !== com.sweattrails.api.formmodes.VIEW) {
                    this.render(com.sweattrails.api.formmodes.VIEW);
                }
            }
        } finally {
            this.ispopup = false;
        }
    };

    onData(data) {
        this.header.onData && this.header.onData(data);
        this.footer.onData && this.footer.onData(data);
        this.ondata && this.ondata();
    };

    onRequestSuccess() {
        this.header.onSuccess && this.header.onSuccess();
        this.footer.onSuccess && this.footer.onSuccess();
        this.onsuccess && this.onsuccess();
    };

    onDataSubmitted() {
        this.close();
        this.header.onDataSubmitted && this.header.onDataSubmitted();
        this.footer.onDataSubmitted && this.footer.onDataSubmitted();
        this.onsubmitted && this.onsubmitted();
    };

    onDataError(errorinfo) {
        this.header.onDataError && this.header.onDataError(errorinfo);
        this.footer.onDataError && this.footer.onDataError(errorinfo);
        const handled = (this.onerror) ? this.onerror(errorinfo) : false;
        if (!handled) this.error("Error saving: " + errorinfo);
    };

    onDataEnd() {
        this.header.onDataEnd && this.header.onDataEnd();
        this.footer.onDataEnd && this.footer.onDataEnd();
        this.ondataend && this.ondataend();
    };

    onRedirect(href) {
        this.header.onRedirect && this.header.onRedirect(href);
        this.footer.onRedirect && this.footer.onRedirect(href);
        this.onredirect && this.onredirect(href);
    };
}

/**
 * FormField - Abstract base class for form elements
 */
com.sweattrails.api.FormField = class com.sweattrails.api.Widget {
    constructor(form, options) {
        super("formfield", form, options);
        this.hidden = false;
        this.modes = options.mode;
        this.readonly = com.sweattrails.api.toBoolean(options.readonly);

        // A FormField is mute when it doesn't interact with the data bridge
        // at all. So it doesn't get any. An example is a header field.
        if (!this.isMute()) {
            let g = null;
            let s = null;
            if (options.property) {
                g = s = options.property;
            } else if (options.get) {
                g = options.get;
                s = options.set || g;
            } else {
                g = s = this.id;
            }
            this.bridge = new com.sweattrails.api.internal.DataBridge(g, s);
        } else {
            this.bridge = null;
        }
        this.onchange = options.onchange && com.sweattrails.api.getfunc(options.onchange);
        this.oninput = options.oninput && com.sweattrails.api.getfunc(options.oninput);
        this.customValidator = options.validate && com.sweattrails.api.getfunc(options.validate);
        this.label = options.label || options.verbose_name || this.id;
        this.required = com.sweattrails.api.toBoolean(options.required);
        const v = options.value || options.default;
        if (v) {
            this.defval = com.sweattrails.api.getfunc(v) || v;
        }
        this.placeholder = options.placeholder;
        this.form.addField(this);
    };

    getId() {
        return this.options.id || this.options.property;
    }

    getElementID(...args) {
        return ["form", this.form.id, this.id, ...args].join("-");
    }

    render(mode, object) {
        if (this.modes && (this.modes.length > 0) && (this.modes.indexOf(mode) < 0)) {
            return false;
        }
        this.mode = mode;
        const val = this.getValueFromObject(object);
        this.log("field(%s).render(%s)", this.id, val)
        const elem = ((this.mode !== com.sweattrails.api.formmodes.VIEW) && !this.readonly) ?
            this.renderEdit(val) :
            this.renderView(val);
        if (!elem.id) {
            elem.id = this.getElementID();
        }
        if ((elem.tagName in ["input", "img", "textarea", "select"]) && !elem.name) {
            elem.name = this.id;
        }
        if (this.form.layout !== "table") {
            this.element = elem;
            this.parent.appendChild(this.element);
        } else {
            if (this.errors) {
                const tr = this.form.newTR();
                const td = document.createElement("td");
                td.colspan = 2;
                td.className = "validationerrors";
                tr.appendChild(td);
                const ul = document.createElement("ul");
                td.appendChild(ul);
                this.errors.forEach(function(e) {
                    const li = document.createElement("li");
                    li.className = "validationerror";
                    li.innerHTML = e.message;
                    ul.appendChild(li);
                });
            }
            this.element = this.form.newTR();
            this.element.id = this.getElementID("fld", "container");
            const lbl = (typeof(this.getLabel) === "function") ? this.getLabel() : this.label;
            if (lbl) {
                const td = document.createElement("td");
                td.className = "formlabel";
                this.element.appendChild(td);
                const label = document.createElement("label");
                label.htmlFor = this.id;
                label.innerHTML = (this.required) ? "(*) " + lbl + ":" : lbl + ":";
                td.appendChild(label);
            }
            const td = document.createElement("td");
            td.className = "formdata";
            if (typeof(this.colspan) === "function") {
                td.colspan = this.colspan();
            } else if (typeof(this.colspan) === "number") {
                td.colspan = this.colspan;
            } else if (!lbl) {
                td.colspan = 2;
            } else {
                td.colspan = 1;
            }
            td.appendChild(elem);
            this.element.appendChild(td);
        }
        this.element.hidden = this.hidden;
        return true;
    };

    erase() {};

    get hidden() {
        return this._hidden;
    };

    set hidden(h) {
        this._hidden = h;
        if (this.element) this.element.hidden = h;
    }

    validate() {
        this.errors = null;
        if (this.customValidator) {
            ST_int.buildErrors(this, this.customValidator(this.getValue()));
        }
        if (this.validator) {
            ST_int.buildErrors(this, this.validator(this.getValue()));
        }
        return this.errors;
    };

    clear() {};

    isMute() {
        return false;
    }

    setValue(value) {
        return (!this.isMute() && this._setValue) ?
            this._setValue(value) :
            false;
    };

    getValue() {
        return (!this.isMute() && this._getValue) ? this._getValue() : null;
    };

    onValueChange() {
        this.onchange && this.onchange(this.getValue());
    };

    onInput() {
        this.oninput && this.oninput(this.getValue());
    };

    assignValueToObject(object) {
        this.log("assignValueToObject");
        if (this.bridge) {
            this.bridge.clear(object);
            this.setValueFromControl(this.bridge, object);
        }
    };

    getValueFromObject(object) {
        let ret = null;
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

    buildInput(type, value = undefined) {
        const control = document.createElement("input");
        control.type = type;
        if (typeof(value) !== 'undefined') {
            control.value = value || "";
        }
        if (this.options) {
            if (this.options.size) {
                control.size = this.options.size;
            }
            if (this.options.maxlength) {
                control.maxLength = this.options.maxlength;
            }
            if (this.options.regexp) {
                control.pattern = "/" + this.options.regexp + "/";
            }
            if (this.options.placeholder) {
                control.placeholder = this.options.placeholder;
            }
            if (com.sweattrails.api.isBoolean(this.options.required)) {
                control.required = com.sweattrails.api.toBoolean(this.options.required);
            }
        }
        return control;
    };

    buildTextInput(elem, value) {
        return this.buildInput("text", value);
    };
}

/**
 * createField - FormField factory method.
 */
com.sweattrails.api.createField(form, options) {
    const type = options.type || options.datatype;
    let factory = (options.factory) && com.sweattrails.api.getfunc(factory);
    if (!factory && type) {
        factory = ST_int.fieldtypes[type];
    }
    if (!factory) {
        this.log(`TYPE ${type} NOT REGISTERED!`);
        this.log("REGISTRY:");
        Object.keys(ST_int.fieldtypes).forEach((t) => {
            this.log(`  ${t} ${"==" ? (type === t) : "!="} ${type}`);
        });
        factory = com.sweattrails.api.internal.fieldtypes.text;
    }
    return com.sweattrails.api.instantiate(factory, form, options);
};

/**
 * FormBuilder -
 */
com.sweattrails.api.FormBuilder = class extends com.sweattrails.api.Builder {
    constructor() {
        super("form", com.sweattrails.api.Form);
        this.processor('field',
            new com.sweattrails.api.Builder('formfield', com.sweattrails.api.createField));
        this.builders = {
            "action": (form, options) => {
                form.footer.buildAction(options);
            },
            "header": (form, options) => {
                form.header.build(options);
            },
            "footer": (form, options) => {
                form.footer.build(options);
            },
        }
    };
}

$$.processor("form", new com.sweattrails.api.FormBuilder());


/* -- F O R M F I E L D  C O N C R E T E  S U B C L A S S E S ------------ */

/*
 * TitleField -
 */
com.sweattrails.api.TitleField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        if (!this.options.level) {
            this.options.level = "3";
        }
        this.colspan = 2;
    };

    renderEdit() {
        this.control = document.createElement(`h${this.options.level}`);
        this.control.innerHTML = this.options.text;
        return this.control;
    };

    renderView() {
        return this.renderEdit();
    };

    getLabel() {
        return null;
    };

    isMute() {
        return true;
    };
}

/*
 * LabelField -
 */
com.sweattrails.api.LabelField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        this.linkedfieldid = options.for || options.field;
        this.assert(this.linkedfieldid, "Label field requires a 'field' attribute")
        if (!this.id) {
            this.id = `${this.linkedfieldid}-label`;
        }
        if (options.label) {
            this.override = options.label;
        } else {
            if (options.text && (options.text !== "")) {
                this.override = options.text;
            }
        }
        this.linkedfield = null;
        this.colspan = 1;
    };

    renderEdit() {
        if (!this.linkedfield) {
            this.linkedfield = this.form.$[this.linkedfieldid];
            $$.assert(this, this.linkedfield, `LabelField: could not resolve field ${this.linkedfieldid}`);
        }
        const lbl = this.override || this.linkedfield.label;
        const label = document.createElement("label");
        label.htmlFor = this.linkedfield.getElementID();
        label.innerHTML = (this.linkedfield.required) ? "(*) " + lbl + ":" : lbl + ":";
        this.control = label;
        return this.control;
    };

    renderView() {
        return this.renderEdit();
    };

    getLabel() {
        return null;
    };

    isMute() {
        return true;
    };
}

/*
 * TextField -
 */
com.sweattrails.api.TextField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
    };

    renderEdit(value) {
        this.control = this.buildInput("text", value);
        this.control.onchange = this.onValueChange.bind(this);
        this.control.oninput = this.onInput.bind(this);
        return this.control;
    };

    setValueFromControl(bridge, object) {
        this.log("setting value %s", this.control.value);
        bridge.setValue(object, this.control.value);
    };

    renderView(value) {
        const ret = document.createElement("span");
        ret.innerHTML = value || "";
        return ret;
    };

    clear() {
        this.setValue("");
    };

    _setValue(value) {
        if (this.control) {
            this.control.value = (value) ? value : "";
        }
    };

    _getValue() {
        return (this.control) ? this.control.value : ""
    };
}

/*
 * PasswordField -
 */
com.sweattrails.api.PasswordField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        this.confirm = com.sweattrails.api.toBoolean(options.confirm);
    };

    renderEdit(value) {
        this.div = document.createElement("div");
        this.div.id = this.getElementID("container");
        this.control = this.buildInput("password", "");
        this.control.value = "";
        this.control.onchange = this.onValueChange.bind(this);
        this.control.input = this.onInput.bind(this);
        this.control.name = this.id;
        this.div.appendChild(this.control);
        if (this.confirm) {
            this.check = this.buildInput("password", "");
            this.check.id = this.getElementID() + "-confirm";
            this.check.name = this.id + "-confirm";
            this.div.appendChild(this.check);
        }
        return this.div;
    };

    validate() {
        if (this.confirm && (this.control.value !== this.check.value)) {
            return "Password values do not match";
        } else {
            return null;
        }
    };

    clear() {
        this.setValue("");
    };

    _setValue(value) {
        if (this.control) {
            this.control.value = value;
            if (this.confirm && this.check) {
                this.check.value = value;
            }
        }
    };

    _getValue() {
        return (this.control) ? this.control.value : ""
    };

    setValueFromControl(bridge, object) {
        this.value = this.control.value;
        bridge.setValue(object, this.control.value);
    };

    renderView(value) {
        const ret = document.createElement("span");
        ret.innerHTML = "*******";
        return ret;
    };
}

/*
 * CheckBoxField -
 */

com.sweattrails.api.CheckBoxField = class extends com.sweattrails.api.FormField {
    constructor(form, elem, parent, options) {
        super(form, elem, parent, options);
    };

    renderEdit(value) {
        this.control = ST_int.buildInput("checkbox");
        this.control.value = true;
        this.control.checked = value;
        this.control.onchange = this.onValueChange.bind(this);
        this.control.oninput = this.onInput.bind(this);
        return this.control;
    };

    setValueFromControl(bridge, object) {
        this.value = this.control.checked;
        bridge.setValue(object, this.value);
    };

    renderView(value) {
        const ret = document.createElement("span");
        if (value) {
            const img = document.createElement("img");
            img.src = this.options.checkmark || "/image/checkmark.png";
            img.height = 24;
            img.width = 24;
            ret.appendChild(img);
        } else if (this.options.unchecked) {
            const img = document.createElement("img");
            img.src = this.options.unchecked;
            img.height = 24;
            img.width = 24;
            ret.appendChild(img);
        } else {
            ret.innerHTML = "&#160;";
        }
        return ret;
    };

    clear() {
        this.setValue(false)
    };

    _setValue(value) {
        if (this.control) {
            this.control.checked = value;
        }
    };

    _getValue() {
        return (this.control) ? this.control.checked : false;
    };
}

/*
 * DateTimeField -
 */

com.sweattrails.api.DateTimeField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        this.date = this.time = true;
        this.timeformat = options.timeformat || "timeofday";
    };

    renderEdit(value) {
        const span = document.createElement("span");
        span.id = this.getElementID("container");
        const d = obj_to_datetime(value);
        let type;
        if (this.date && !this.time) {
            type = "date";
        } else if (this.time && !this.date) {
            type = "time";
        } else {
            type = "datetime";
        }
        this.control = this.buildInput(type);
        d && (this.control.valueAsDate = d);
        this.control.onchange = this.onValueChange.bind(field);
        this.control.oninput = this.onInput.bind(field);
        this.control.id = this.getElementID();
        this.control.name = this.id;
        span.appendChild(this.control);
        return span;
    };

    setValueFromControl(bridge, object) {
        var v = this.control.valueAsDate;
        this.value = (v) ? datetime_to_obj(v) : null;
        bridge.setValue(object, this.value);
    };

    renderView(value) {
        const ret = document.createElement("span");
        if (value) {
            let t = "";
            if (this.time) {
                if (typeof(value.hour) === "undefined") {
                    value = seconds_to_timeobj(value)
                }
                if ((typeof(this.timeformat) !== "undefined") && (this.timeformat === "duration")) {
                    t = prettytime(value);
                } else {
                    t = format_time(value);
                }
            }
            ret.innerHTML = (this.date && (format_date(value) + " ") || "") + t;
        } else {
            ret.innerHTML = "&#160;";
        }
        return ret;
    };

    clear() {
        this.setValue(null);
    };

    _setValue(value) {
        if (this.control) {
            this.control.valueAsDate = value;
        }
    };

    _getValue() {
        return (this.control) ? this.control.valueAsDate : null;
    };
};

/*
 * DateField - Use DateTimeField, just without the time bits
 */
com.sweattrails.api.DateField = class extends com.sweattrails.api.DateTimeField {
    constructor(form, options) {
        super(form, options);
        this.time = false;
    };
};

/*
 * TimeField - Use DateTimeField, just without the date bits
 */
com.sweattrails.api.TimeField = class extends com.sweattrails.api.DateTimeField {
    constructor(form, options) {
        super(form, options);
        this.date = false;
    };
};

/*
 * FileField -
 */
com.sweattrails.api.FileField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        this.multiple = com.sweattrails.api.toBoolean(options.multiple);
    };

    renderEdit(value) {
        this.control = this.buildInput("file");
        if (this.multiple) this.control.multiple = true;
        this.control.onchange = this.onValueChange.bind(this);
        this.control.oninput = this.onInput.bind(this);
        return this.control;
    };

    setValueFromControl(bridge, object) {
        var files = this.control.files;
        if (files) {
            if (this.multiple) {
                this.log(`#files: ${files.length}`)
                Array.from(files).forEach((f, ix) => {
                    this.log(`file[${ix}]: ${files[ix].name}`);
                });
            } else {
                this.log(`file: ${files[0].name}`);
            }
        } else {
            this.log("this.control.files undefined...");
        }
        this.value = (this.multiple) ? this.control.files : this.control.files[0];
        bridge.setValue(object, this.value);
    };

    /* TODO Better presentation (MIME type icons) */
    renderView(value) {
        var ret = document.createElement("span");
        ret.innerHTML = "<i>... File ...</i>";
        return ret;
    };

    clear() {
        this.setValue(null);
    };

    _setValue(value) {
        // FIXME..
        if (this.control) {
            this.log("FileField.setValue not implemented...");
        }
    };

    _getValue() {
        this.log("FileField.getValue not implemented...");
        return null;
    };
};

/*
 * IconField -
 */

com.sweattrails.api.IconField = class extends com.sweattrails.api.FormField {
    constructor(form, options) {
        super(form, options);
        this.height = options.height || 48;
        this.width = options.width || 48;
        this.readonly = true;
    };

    build() {
        if (this.datasource) {
            // this.submitParameter(elem.getAttribute("imageparameter") || "image",
            //     (function() {return this.control.files[0];}).bind(this));
            // this.submitParameter(elem.getAttribute("contenttypeparameter") || "contentType",
            //     (function() {return this.control.files[0].type;}).bind(this));
            this.datasource.submitAsJSON = false;
        }
    }

    renderEdit(value) {
        return null;
    };

    getValueFromControl(bridge, object) {
        return null;
    };

    _getValue() {
        console.log(" IconField.getValue not implemented...");
        return null;
    };

    renderView(value) {
        const div = document.createElement("div");
        if (this.url && (this.mode === com.sweattrails.api.formmodes.VIEW)) {
            div.ondragenter = () => {
                this.entered++;
                this.control.style.display = 'block';
            };
            div.ondragleave = () => {
                this.entered--;
                if (!this.entered) this.control.style.display = 'none';
            };
        }

        const img = document.createElement("img");
        img.src = value;
        img.height = this.height;
        img.width = this.width;
        div.appendChild(img);

        if (this.datasource && (this.mode === com.sweattrails.api.formmodes.VIEW)) {
            this.control = document.createElement("input");
            this.control.name = this.id;
            this.control.id = this.id;
            this.control.type = "file";
            this.control.style.display = "none";
            this.control.style.position = "absolute";
            this.control.style.top = this.control.style.left = this.control.style.right = this.control.style.bottom = 0;
            this.control.style.opacity = 0;

            this.control.onchange = () => {
                this.datasource.createObjectFrom(this.form.datasource.getObject());
                this.datasource.submit();
            }
            div.appendChild(this.control);
        }
        return div;
    };

    onDataSubmitted() {
        this.form.render();
    };

    onDataError() {
        this.form.render();
    };

    hasDatasource() {
        return true;
    }
};

ST_int.fieldtypes.text = com.sweattrails.api.TextField;
ST_int.fieldtypes.TextProperty = com.sweattrails.api.TextField;
ST_int.fieldtypes.StringProperty = com.sweattrails.api.TextField;
ST_int.fieldtypes.LinkProperty = com.sweattrails.api.TextField;
ST_int.fieldtypes.integer = com.sweattrails.api.IntField;
ST_int.fieldtypes.title = com.sweattrails.api.TitleField;
ST_int.fieldtypes.label = com.sweattrails.api.LabelField;
ST_int.fieldtypes.password = com.sweattrails.api.PasswordField;
ST_int.fieldtypes.PasswordProperty = com.sweattrails.api.TextField;

ST_int.fieldtypes.checkbox = com.sweattrails.api.CheckBoxField;
ST_int.fieldtypes.boolean = com.sweattrails.api.CheckBoxField;
ST_int.fieldtypes.bool = com.sweattrails.api.CheckBoxField;
ST_int.fieldtypes.BooleanProperty = com.sweattrails.api.CheckBoxField;

ST_int.fieldtypes.date = com.sweattrails.api.DateField;
ST_int.fieldtypes.DateProperty = com.sweattrails.api.DateField;
ST_int.fieldtypes.datetime = com.sweattrails.api.DateTimeField;
ST_int.fieldtypes.DateTimeProperty = com.sweattrails.api.DateTimeField;
ST_int.fieldtypes.time = com.sweattrails.api.TimeField;
ST_int.fieldtypes.TimeProperty = com.sweattrails.api.TimeField;

ST_int.fieldtypes.file = com.sweattrails.api.FileField;
ST_int.fieldtypes.icon = com.sweattrails.api.IconField;
ST_int.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
