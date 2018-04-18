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

/* -- B A S I C T A B ---------------------------------------------------- */

com.sweattrails.api.BasicTab = class {
    constructor() {
        this.onSelect = null;
        this.onUnselect = null;
        this.onDraw = null;
    }
}

/* -- T A B -------------------------------------------------------------- */

com.sweattrails.api.internal.Tab = class extends __.Component {
    constructor(container, options = {}) {
        super("tab", container, options);
        this.impl = null;
        this.code = options.code || this.id;
        this.label = options.label || this.code;
        if (elem.getAttribute("factory")) {
            this.impl = __.getfunc(elem.getAttribute("factory"))(this);
        } else if (elem.getAttribute("impl")) {
            this.impl = new __.getfunc(elem.getAttribute("impl"))(this);
        } else {
            this.impl = null;
        }
        if (this.impl) {
            __.mixin(this, this.impl);
        }
        this.container.addTab(this);
    }

    build(elem, options) {
        const tabbox = this.container.tabbox;
        const span = document.createElement("span");
        span.className = "tab";
        span.id = `${this.container.id}-tab-${tab.id}`;
        span.tab = tab;
        span.onclick = this.select.bind(this.container, tab.code);
        tabbox.appendChild(span);
        this.header = span;
        this.href = document.createElement("a");
        this.href.className = "greylink";
        this.href.href = "#";
        this.href.innerHTML = tab.label;
        this.href.tab = tab;
        span.appendChild(tab.href);

        this.page = document.createElement("div");
        this.page.id = `${this.container.id}-page-${tab.id}`;
        this.page.className = "tabpage";
        this.page.hidden = true;
        this.container.pagebox.appendChild(tab.page);
        this.draw && this.draw()
    }

    select() {
        if (this.onSelect) {
            this.onSelect();
        }
        this.onSelect && this.onSelect();
        this.components.forEach((component) => {
            if (component && component.render) {
                component.render();
            }
        });
        this.header.className = "tab_selected";
        this.header.className = "tab_selected";
        this.href.className = "whitelink";
        this.page.hidden = false;
    }

    unselect() {
        this.onUnselect && this.onUnselect();
        this.header.className = "tab";
        this.href.className = "greylink";
        this.page.hidden = true;
    };
};

/* -- T A B B A R -------------------------------------------------------- */

com.sweattrails.api.TabBar = class extends __.Component {
    constructor(container, options) {
        super("tabs", container, options);
        this.tabs = {}
        this.firsttab = null;
        this.element = document.createElement('div');
        this.element.id = `tabs-${this.id}`;
        this.element.className = 'tabs';
    };

    select(code, ev) {
        this.selectTab(code);
        ev.stopPropagation();
    };

    build(elem, options) {
        this.tabbox = document.createElement('div');
        this.tabbox.id = `pagebox-${id}`;
        this.tabbox.width = '100%';
        this.pagebox = document.createElement('div');
        this.pagebox.id = `pagebox-${id}`;
        this.pagebox.width = '100%';
        this.pleasewait = document.createElement('div');
        this.pleasewait.className = 'tabpage';
        this.pleasewait.id = `tabs-${this.id}-page-pleasewait`
        const pw_span = document.createElement('span');
        pw_span.style.textAlign = 'center';
        const throbber = document.createElement('img');
        throbber.src = '/image/throbber.gif';
        throbber.height = throbber.width = 32
        pw_span.appendChild(throbber);
        pw_span.appendChild(document.createTextNode('&#160;Please wait'));
        this.pleasewait.appendChild(pw_span);
        this.pagebox.appendChild(this.pleasewait);
        this.element.appendChild(this.tabbox);
        this.element.appendChild(this.pagebox);
        // <div class="tabs" id="tabs-${id}">
        //     <div class="tabbox" id="tabbox-${id}">
        //     </div>
        //     <div class="pagebox" id="pagebox-${id}" width="100%">
        //         <div id="tabs-${id}-page-pleasewait" class="tabpage">
        //             <span style="text-align: center;">
        //                 <img src="/image/throbber.gif" height="32" width="32"/>
        //                 &#160;Please wait
        //             </span>
        //         </div>
        //         {% block tabs %}
        //         {% endblock tabs %}
        //     </div>
        // </div>
    };

    start() {
        if (this.pleasewait) {
            this.pleasewait.hidden = true;
        }
        if (this.firsttab) {
            this.selectTab(this.firsttab.code);
        }
    }

    addTab(tab) {
        $$.log(this, `addTab(${tab.code})`);
        this.firsttab = this.firsttab || tab;
        if (!tab.onDraw || tab.onDraw()) {
            this.tabs[tab.code] = tab;
            return tab;
        } else {
            $$.log(this, `Tab ${tab.code} hidden`);
            return null;
        }
    }

    selectTab(code) {
        $$.log(this, `selectTab(${code})`);
        const newtab = this.tabs[code];
        if (newtab) {
            Object.values(this.tabs)
                .filter((tab) => (tab.header.className === "tab_selected") && (tab.code !== code))
                .forEach((tab) => {
                    tab.unselect()
                });
            if (newtab.header.className !== 'tab_selected') {
                newtab.select();
            }
            return true;
        }
        return false;
    }
};

/* -- T A B B U I L D E R ------------------------------------------------ */

com.sweattrails.api.TabBuilder = class extends __.Builder {
    constructor() {
        super("tab", ___.Tab);
    };

    isContainer() {
        return true;
    }
};

/* -- T A B S B U I L D E R ---------------------------------------------- */

com.sweattrails.api.TabsBuilder = class extends __.Builder {
    constructor() {
        super("tabs", __.TabBar);
        this.processor('tab', new com.sweattrails.api.TabBuilder());
    };
};

$$.processor("tabs", new com.sweattrails.api.TabBuilder());
