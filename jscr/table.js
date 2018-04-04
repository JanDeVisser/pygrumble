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


com.sweattrails.api.Column = class {
    constructor(elem, table) {
        let g = null;

        this.elem = elem;
        this.width = elem.getAttribute("width");
        this.align = elem.getAttribute("align");
        this.link = elem.getAttribute("link");
        if (elem.getAttribute("property")) {
            g = elem.getAttribute("property");
        } else {
            g = elem.getAttribute("get");
        }
        this.bridge = new com.sweattrails.api.internal.DataBridge(g);
        this.table = table;
        this.label = elem.getAttribute("label");

        if (elem.getAttribute("select") && !this,table.form) {
            this.impl = new com.sweattrails.api.LinkColumn(this, elem);
        }
        if (!this.impl) {
            const type = elem.getAttribute("type");
            if (type) {
                this.createImpl(type, this, elem);
            }
        }
    }

    createImpl(type, ...args) {
        if (type) {
            const factory = com.sweattrails.api.internal.columntypes[type];
            if (factory) {
                try {
                    this.impl = factory(...args);
                } catch (e) {
                    this.impl = new factory(...args);
                }
            }
        }
    }

    applyPropertyDef(propdef) {
        if (!this.label && propdef.verbose_name) {
            this.label = propdef.verbose_name;
        }
        if (!this.impl) {
            this.createImpl(propdef.type, this, this.elem);
        }
    }


    getValue(object) {
        let ret = this.bridge.getValue(object, this);
        if (!this.impl) {
            this.createImpl(typeof(ret), this, this.elem, ret);
        }
        if (this.impl) {
            ret = this.impl.format(ret, object);
        }
        if (this.link && this.table.form) {
            const f = (function(object) {
                if (!this.form.ispopup) {
                    this.data = object;
                    this.form.popup();
                }
            }).bind(this.table, object);
            ret = new com.sweattrails.api.Link(f, ret);
        }
        return ret;
    }
}

/*
 * Table -
 */
com.sweattrails.api.Table = class {
    constructor(container, id, ds = null) {
        this.container = container;
        this.id = id;
        this.type = "table";
        $$.register(this);
        this.table = null;
        if (ds) {
            this.setDataSource(ds);
        }
        this.columns = [];
        this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
        this.header = new com.sweattrails.api.ActionContainer(this, "header");
    };

    initForm(ds) {
        this.form = new com.sweattrails.api.Form("table-" + this.id, this.container, ds, true);
    //        new com.sweattrails.api.ProxyDataSource(this), true)
        return this;
    };

    setDataSource(ds) {
        this.datasource = ds;
        ds.addView(this);
        return this;
    };

    addColumns(...args) {
        args.forEach((col) => {
            this.columns.push(col);
        });
        return this;
    };

    render() {
        $$.log(this, "render()");
        this.datasource.reset();
        this.datasource.execute();
        this.header.erase();
        this.footer.erase();
        if (this.table) {
            this.container.removeChild(this.table);
        }
        this.header.render();
        return this;
    };

    onData(data) {
        $$.log(this, "Table.onData");
        this.onrender && this.onrender(data);
        this.table = document.createElement("table");
        this.table.id = this.id + "-table";
        this.table.width = "100%";
        this.cellspacing = "0";
        this.container.appendChild(this.table);
        this.headerrow = document.createElement("tr");
        this.headerrow.id = `${this.id}-header`;
        this.headerrow.className = "tableheader";
        this.table.appendChild(this.headerrow);
        this.rowclass = 'oddrow';

        if (this.counter) {
            const th = document.createElement("th");
            th.innerHTML = "#";
            this.headerrow.appendChild(th);
        }
        this.columns.forEach((col) => {
            const th = document.createElement("th");
            if (col.width) {
                th.width = col.width;
            }
            th.innerHTML = col.label || col.bridge.get;
            this.headerrow.appendChild(th);
        });
        this.count = 0;
    };

    noData() {
        $$.log(this, "Table.noData");
        var emptyrow = document.createElement("div");
        emptyrow.id = this.id + "-emptyrow";
        this.container.appendChild(emptyrow);
        emptyrow.innerHTML = "&#160;<i>No data</i>";
    };

    renderData(obj) {
        if (this.datasource.debug) {
            $$.dump(obj, `${$$.objectlabel(this)}Table.renderData`);
        }
        if (!obj) return;
        const tr = document.createElement("tr");
        tr.className = this.rowclass;
        this.rowclass = (this.rowclass === 'oddrow') ? 'evenrow' : 'oddrow';
        this.count++;
        if (this.counter) {
            const td = document.createElement("td");
            td.style.textAlign = "center";
            td.innerHTML = "" + this.count + ".";
            tr.appendChild(td);
        }
        this.columns.forEach((coldef) => {
            const td = document.createElement("td");
            if (coldef.align) td.style.textAlign = coldef.align;
            let data = coldef.getValue(obj);
            if (!data) {
                if (typeof(obj.render) === 'function') {
                    data = obj.render(i, coldef);
                }
            }
            com.sweattrails.api.renderObject(td, data);
            tr.appendChild(td);
        });
        this.table.appendChild(tr);
    };

    onDataEnd() {
        $$.log(this, "Table.onDataEnd");
        this.footer.render();
        this.onrendered && this.onrendered();
    };

    onMetadata(metadata) {
        const props = metadata.schema.properties.reduce((props, p) => {
            props[p.name] = p;
            return props;
        }, {});
        this.columns.forEach((coldef) => {
            if (coldef.bridge.get in props) {
                coldef.applyPropertyDef(props[coldef.bridge.get]);
            }
        });
    }

    openForm(object) {
        $$.log(this, "Table.openForm");
        if (this.form && !this.form.ispopup) {
            this.data = object;
            this.form.popup((!object) ? com.sweattrails.api.MODE_NEW : com.sweattrails.api.MODE_VIEW);
        }
        return true;
    };

    reset(data) {
        $$.log(this, "Table.reset");
        this.datasource.reset(data);
        this.render();
    };

    getProxyData() {
        return this.data;
    };

    submitProxyData() {
        this.datasource.submit();
    };

    pushProxyState(state) {
        this.datasource.pushState(state);
    };

    popProxyState() {
        this.datasource.popState();
    };

    onDataSubmitted() {
        $$.log(this, "Table.onDataSubmitted");
        this.form && this.form.ispopup && this.form.onDataSubmitted();
        this.onsubmitted && this.onsubmitted();
    };

    onDataError(errorinfo) {
        $$.log(this, "Table.onDataError");
        this.form && this.form.ispopup && this.form.onDataError(errorinfo);
        this.onerror && this.onerror(errorinfo);
    };
}

/**
 * TableBuilder -
 */

com.sweattrails.api.TableBuilder = class {
    constructor() {
        this.type = "builder";
        this.name = "tablebuilder";
        com.sweattrails.api.STManager.processor("table", this);
    };

    process(t) {
        const p = t.parentNode;
        const name = t.getAttribute("id") || t.getAttribute("name");
        $$.log(this, `Building table ${name}`);
        const ds = com.sweattrails.api.dataSourceBuilder.build(t);
        const table = new com.sweattrails.api.Table(p, name, ds);
        table.onrender = t.getAttribute("onrender") && __.getfunc(t.getAttribute("onrender"));
        table.onrendered = t.getAttribute("onrendered") && __.getfunc(t.getAttribute("onrendered"));
        table.footer.build(t);
        const footer = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "footer");
        if (footer.length === 1) {
            table.footer.build(footer[0]);
        }
        const header = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "header");
        if (header.length === 1) {
            table.header.build(header[0]);
        }
        const forms = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "dataform");
        if (forms.length === 1) {
            const formelem = forms[0];
            const form_ds = com.sweattrails.api.dataSourceBuilder.build(formelem,
                                new com.sweattrails.api.ProxyDataSource(table));
            table.initForm(form_ds);
            _.formbuilder.buildForm(table.form, formelem);
        }
        table.counter = t.getAttribute("counter") != null;
        getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "column")
            .forEach((c) => {
                table.addColumns(new com.sweattrails.api.Column(c, table));
            });
    };
};

_.tablebuilder = new com.sweattrails.api.TableBuilder();

/* ------------------------------------------------------------------------ */

com.sweattrails.api.Image = class {
    constructor(url, alttext = null) {
        this.url = url;
        this.alttext = alttext;
        ret.height = "24px";
        ret.width = "24px";
    };

    render() {
        const img = document.createElement("img");
        img.src = this.url;
        if (this.width) img.width = this.width;
        if (this.height) img.height = this.height;
        if (this.alttext) img.alt = this.alttext;
        return img;
    };
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.Link = class {
    constructor(url, display, object = {}, ...parameters) {
        this.url = url;
        if (typeof(this.url) !== 'function') {
            this.url = this.url.replace('$$', display)
                               .replace(/\$([\w]+)/g, (match, submatch) => object[submatch]);
        }
        this.display = display || "&#160;";
        this.parameters = [];
        parameters.forEach((p) => {
            this.parameters.push(p);
        });
    };

    render() {
        const a = document.createElement("a");
        if (typeof(this.url) === "function") {
            a.href = "#";
            a.onclick = this.url;
        } else {
            a.href = this.url;
            if (this.parameters.length > 0) {
                a.href += this.parameters
                              .reduce((params, [p, v], ix) => {
                                  if (ix > 0) {
                                      params += "&";
                                  }
                                  params += `${encodeURIComponent(p)}=${encodeURIComponent(v)}`;
                                  return params;
                               }, "?");
            }
        }
        com.sweattrails.api.renderObject(a, this.display);
        return a;
    };
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.internal.ColumnImpl = class {
    constructor(col, elem) {
        this.column = col;
    }
}

com.sweattrails.api.IntColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    format(value, object) {
        return String(new Number(value).toFixed(0));
    }
};

com.sweattrails.api.FloatColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    constructor(col, elem) {
        super(col, elem);
        this.digits = elem.getAttribute("digits");
    };

    format(value, object) {
        return (this.digits !== null)
            ? String(new Number(value).toFixed(this.digits))
            : String(value);
    };
};

com.sweattrails.api.BooleanColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    constructor(col, elem) {
        super(col, elem);
        this.checkmark = elem.getAttribute("checkmark") || "/images/checkmark.png";
        this.failmark = elem.getAttribute("failmark");
    };

    format(value, object) {
        let ret = null;
        if (value) {
            ret = new com.sweattrails.api.Image(this.checkmark);
        } else if (this.failmark) {
            ret = new com.sweattrails.api.Image(this.failmark);
        }
        return ret;
    }
};

com.sweattrails.api.TimeColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    format(value, object) {
        return prettytime(seconds_to_time(value));
    }
};

com.sweattrails.api.DateColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    format(value, object) {
        return format_date(value)
    }
};

com.sweattrails.api.DateTimeColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    format(value, object) {
        return format_datetime(value)
    }
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.LinkColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    constructor(col, elem) {
        super(col, elem);
        this.url = elem.getAttribute("url") || elem.getAttribute("select");
        this.parameters = [];
        Array.from(getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "parameter"))
             .forEach((p) => {
                 const n = p.getAttribute("name");
                 if (!n) return;
                 const v = p.getAttribute("value") || n;
                 this.parameters.push([n, v]);
             });
    };

    format(value, object) {
        return new com.sweattrails.api.Link(this.url, value, object, ...this.parameters);
    };
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.IconColumn = class extends com.sweattrails.api.internal.ColumnImpl {
    constructor(col, elem) {
        super(col, elem);
        col.align = 'center';
        this.icons = {};
        if (elem.getAttribute("url")) {
            this.url = elem.getAttribute("url");
        } else {
            getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "icon")
                .forEach((i) => {
                    this.icons[i.getAttribute("value")] = i.getAttribute("icon");
            });
        }
        this.size = elem.getAttribute("iconsize");
        this.width = elem.getAttribute("iconwidth");
        this.height = elem.getAttribute("iconheight");
    }

    format(value, object) {
        let url;
        if (this.url) {
            url = this.url
                       // Replace occurences of $$ with column value:
                      .replace('$$', value)
                       // Replace occurrences of $<attribute> with <attribute> value:
                      .replace(/\$([\w]+)/g, (match, submatch) => object[submatch]);
        } else if (value in this.icons) {
            url = this.icons[value];
        } else {
            url = value;
        }
        // If the URL is not fully qualified assume it refers to a .png in /image:
        if (!url.match(/^(\/.+)|(https?:\/\/.+)/)) {
            url = `/image/${url}.png`;
        }
        const ret = new com.sweattrails.api.Image(url);
        ret.height = this.height || this.size || "24";
        ret.width = this.width || this.size || "24";
        return ret;
    };
};

/* ------------------------------------------------------------------------ */

com.sweattrails.api.internal.objectColumnFactory = function(col, elem, value) {
    if (("year" in value) && ("month" in value) && ("day" in value)) {
        if (("hour" in value) && ("minute" in value)) {
            return new com.sweattrails.api.DateTimeColumn(col, elem, value);
        } else {
            return new com.sweattrails.api.DateColumn(col, elem, value);
        }
    } else if (("hour" in value) && ("minute" in value)) {
        return new com.sweattrails.api.TimeColumn(col, elem, value);
    } else {
        const name = value.__proto__.constructor.name;
        if (name !== "Object") {
            factory = ST_int.columntypes[name];
            if (factory) {
                return new factory()
            }
        }
    }
    return null;
}

/* ------------------------------------------------------------------------ */

ST_int.columntypes = {};
ST_int.columntypes.int = com.sweattrails.api.IntColumn;
ST_int.columntypes.integer = com.sweattrails.api.IntColumn;
ST_int.columntypes.IntegerProperty = com.sweattrails.api.IntColumn;
ST_int.columntypes.IntProperty = com.sweattrails.api.IntColumn;
ST_int.columntypes.float = com.sweattrails.api.FloatColumn;
ST_int.columntypes.FloatProperty = com.sweattrails.api.FloatColumn;
ST_int.columntypes.number = com.sweattrails.api.FloatColumn;
ST_int.columntypes.boolean = com.sweattrails.api.BooleanColumn;
ST_int.columntypes.BooleanProperty = com.sweattrails.api.BooleanColumn;
ST_int.columntypes.DateTimeProperty = com.sweattrails.api.DateTimeColumn;
ST_int.columntypes.DateProperty = com.sweattrails.api.DateColumn;
ST_int.columntypes.TimeProperty = com.sweattrails.api.TimeColumn;
ST_int.columntypes.icon = com.sweattrails.api.IconColumn;
ST_int.columntypes.link = com.sweattrails.api.LinkColumn;
ST_int.columntypes.object = com.sweattrails.api.internal.objectColumnFactory;
