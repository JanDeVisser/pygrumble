if (typeof(com) !== 'object') {
    var com = {}
}
com.sweattrails = {}
com.sweattrails.api = {}
com.sweattrails.api.internal = {}
com.sweattrails.api.prototypes = {}

com.sweattrails.author = "Jan de Visser"
com.sweattrails.copyright = "(c) Jan de Visser 2012 under the BSD License"
com.sweattrails.api.xmlns = "http://www.sweattrails.com/html"

if (typeof(ST) !== 'object') {
    var ST = com.sweattrails.api
}

if (typeof(Object.create) !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o
        return new F()
    }
}

com.sweattrails.api.Manager = function() {
    this.id = "APIManager"
    this.type = "manager"
    this.components = []
    this.processors = []
    this.objects = {}
    this.register(this)
}

com.sweattrails.api.Manager.prototype.register = function(c) {
    var t = c.type
    var what = t
            || (c.__proto__ && c.__proto__.constructor && c.__proto__.constructor.name)
            || "unknown"
    var name = c.id || c.name
    if (name) {
        (this[what] || (this[what] = {})) && (this[what][name] = c)
        t && (this[t] || (this[t] = {})) && (this[t][name] = c)
        this.objects[name] = c
    } else {
        (this[what] || (this[what] = [])) && this[what].push(c)
        t && (this[t] || (this[t] = [])) && this[t].push(c)
    }
    this.components.push(c)
    if (c.container && c.render && this.objects.TabManager) {
        var elem = c.container
        var renderables = this.objects.TabManager.renderables
        for (var p = elem; p != null; p = p.parentNode) {
            if (p.className == "tabpage") {
                renderables = this.tab[p.id.substring(5)].renderables
                break
            }
        }
        renderables.push(c)
    }
    console.log(this.id + ": registered: " + name + ", type " + t + " (" + this.components.length + ")")
}

com.sweattrails.api.Manager.prototype.processor = function(tagname, processor) {
    this.register(processor)
    var p = { tagname: tagname, processor: processor }
    this.processors.push(p)
}

com.sweattrails.api.Manager.prototype.get = function(id) {
    return this.objects[id]
}

com.sweattrails.api.Manager.prototype.all = function(type) {
    return this[type]
}

com.sweattrails.api.Manager.prototype.process = function() {
    for (var pix = 0; pix < this.processors.length; pix++) {
        var p = this.processors[pix]
        var tagname = p.tagname
        var processor = p.processor
        var elements = document.getElementsByTagNameNS(com.sweattrails.api.xmlns, tagname)
        this.log(this, "build(" + tagname + "): found " + elements.length + " elements")
        for ( ; elements.length > 0; ) {
            var element = elements[0]
            var parent = element.parentNode
            processor.process(element)
            parent.removeChild(element)
        }
    }
}

com.sweattrails.api.Manager.prototype.run = function() {
    this.dispatch("load")
    this.log(this, "Loaded")
    this.dispatch("build")
    this.log(this, "Built")
    this.process()
    this.log(this, "Processed")
    this.dispatch("start")
    this.log(this, "Started")
}

com.sweattrails.api.Manager.prototype.render = function(id) {
    this.executeOn(id, "render")
}

com.sweattrails.api.Manager.prototype.executeOn = function(id, func) {
    var obj = this.objects[id]
    obj && obj[func] && obj[func]()
}

com.sweattrails.api.Manager.prototype.dispatch = function(d) {
    for (var ix = 0; ix < this.components.length; ix++) {
        var c = this.components[ix]
        c[d] && c[d]()
    }
}

com.sweattrails.api.Manager.prototype.log = function(obj, msg) {
    var o = obj.type + ((obj.id || obj.name) && ("(" + (obj.id||obj.name) + ")"))
    console.log(o + ": " + msg)
}

com.sweattrails.api.STManager = new com.sweattrails.api.Manager()

function $(id) {
    return com.sweattrails.api.STManager.get(id)
}

function _$(type) {
    return com.sweattrails.api.STManager.all(type)
}

$$ = com.sweattrails.api.STManager
_ = $$.objects

com.sweattrails.api.BasicTab = function() {
    this.onSelect = null
    this.onUnselect = null
    this.onDraw = null
    return this
}

com.sweattrails.api.internal.Tab = function(code, label, elem) {
    this.type = "tab"
    this.impl = null
    if (elem) {
        var factory = null
        if (elem.getAttribute("factory")) {
            factory = new Function("tab", "return " + elem.getAttribute("factory") + "(tab)")
        } else if (elem.getAttribute("impl")) {
            factory = new Function("return new " + elem.getAttribute("impl") + "()")
        }
        this.impl = factory && factory(elem)
        this.renderables = []
        this.code = code
        this.id = this.code
        this.label = label
        if (this.impl) {
            this.impl.initialize && this.impl.initialize(elem)
            this.impl.code = this.code
            this.impl.label = this.label
        }
    }
    com.sweattrails.api.STManager.register(this)
    return this
}

com.sweattrails.api.internal.Tab.prototype.select = function() {
    if (this.impl && this.impl.onSelect) {
        this.impl.onSelect()
    }
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix]
        if (!renderable.container.hidden || (renderable.container.className == "tabpage")) {
            renderable.render()
        }
    }
    this.header.className = "tab_selected"
    this.href.className = "whitelink"
    this.page.hidden = false
}

com.sweattrails.api.internal.Tab.prototype.unselect = function() {
    if (this.impl && this.impl.onUnselect) {
        impl.onUnselect()
    }
    this.header.className = "tab"
    this.href.className = "greylink"
    this.page.hidden = true
}

com.sweattrails.api.TabManager = function() {
    if (com.sweattrails.api.tabManager != null) {
    	alert("TabManager is a singleton!")
    	return null
    }
    this.id = "TabManager"
    this.type = "manager"
    com.sweattrails.api.STManager.register(this)
    this.renderables = []
    this.tabs = {}
    this.firsttab = null
    this.select = function(code, ev) { this.selectTab(code); ev.stopPropagation() }
    return this
}

com.sweattrails.api.TabManager.prototype.build = function() {
    this.pagebox = document.getElementById("pagebox")
    if (!this.pagebox) return
    var tb = this.pagebox.getElementsByTagNameNS(com.sweattrails.api.xmlns, "tabs")
    if (tb && (tb.length > 0)) {
        tabs_elem = tb[0]
        var tabs = getChildrenByTagNameNS(tabs_elem, com.sweattrails.api.xmlns, "tab")
        $$.log(this, "Found " + tabs.length + " tabs")
        for (var tabix = 0; tabix < tabs.length; tabix++) {
            var tab_elem = tabs[tabix]
            var tab = this.addTabFromElem(tab_elem)
            this.firsttab = this.firsttab || tab
            tabs_elem.removeChild(tab_elem)
        }
    }
}

com.sweattrails.api.TabManager.prototype.start = function() {
    var pw = document.getElementById("page_pleasewait")
    pw.hidden = true
    for (var rix = 0; rix < this.renderables.length; rix++) {
        var renderable = this.renderables[rix]
        if (renderable && renderable.render) {
            renderable.render()
        }
    }
    if (this.firsttab != null) {
        this.selectTab(this.firsttab.code)
    }
}

com.sweattrails.api.TabManager.prototype.addTabFromElem = function(elem) {
    tab = this.addTab(new com.sweattrails.api.internal.Tab(elem.getAttribute("code"), elem.getAttribute("label"), elem))
    if (tab) {
        while (elem.childNodes.length > 0) {
            tab.page.appendChild(elem.childNodes[0])
        }
    }
    return tab
}

com.sweattrails.api.TabManager.prototype.addTab = function(tab) {
    $$.log(this, "addTab(" + tab.code + ")")
    if ((tab.impl == null) || (tab.impl.onDraw == null) || tab.impl.onDraw()) {
        this.drawTab(tab)
        this.tabs[tab.code] = tab
    } else {
        $$.log(this, "Tab " + tab.code + " hidden")
        tab = null
    }
    return tab
}

com.sweattrails.api.TabManager.prototype.drawTab = function(tab) {
    $$.log(this, "Tab " + tab.code + " visible")
    var onclick = this.select.bind(this, tab.code)
    tab.manager = this
    var tabbox = document.getElementById("tabbox")
    var span = document.createElement("span")
    span.className = "tab"
    span.id = "tab_" + tab.code
    span.tab = tab
    span.onclick = onclick
    tabbox.appendChild(span)
    tab.header = span
    tab.href = document.createElement("a")
    tab.href.className = "whitelink"
    tab.href.href = "#"
    tab.href.innerHTML = tab.label
    tab.href.tab = tab
    tab.href.onclick = onclick
    span.appendChild(tab.href)

    tab.page = document.getElementById("page_" + tab.code)
    if (tab.page == null) {
        tab.page = document.createElement("div")
        tab.page.id = "page_" + tab.code
        tab.page.className = "tabpage"
        tab.page.hidden = true
        this.pagebox.appendChild(tab.page)
    }
}


com.sweattrails.api.TabManager.prototype.selectTab = function(code) {
    //$$.log(this, "selectTab(" + code + ")")
    for (var tabcode in this.tabs) {
        var tab = this.tabs[tabcode]
        if (code == tab.code) {
            if (tab.header.className != "tab_selected") {
                tab.select()
            }
        } else if (tab.header.className == "tab_selected") {
            tab.unselect()
        }
    }
    return true
}

com.sweattrails.api.tabManager = new com.sweattrails.api.TabManager()

com.sweattrails.api.internal.DataBridge = function() {
    this.get = null
    this.set = null
}

com.sweattrails.api.internal.DataBridge.prototype.setValue = function(object, value) {
    var s = this.set || this.get
    if (typeof(s) == "function") {
    	s(object, value)
    } else if (s) {
        var p = s
        var o = object
        for (var dotix = p.indexOf("."); (dotix > 0) && (dotix < (p.length-1)); dotix = p.indexOf(".")) {
            var subp = p.substring(0, dotix)
            if (o) {
                if (!o[subp]) o[subp] = {}
                o = o[subp]
            }
            p = p.substring(dotix + 1)
        }
        if (o) o[p] = value
    }
}


com.sweattrails.api.internal.DataBridge.prototype.getValue = function(object, context) {
    var ret = null
    if (typeof(this.get) == "function") {
    	ret = this.get(object, context)
    } else if (this.get != null) {
        var p = this.get
        var o = object
        for (var dotix = p.indexOf("."); (dotix > 0) && (dotix < (p.length-1)); dotix = p.indexOf(".")) {
            o = o && o[p.substring(0, dotix)]
            p = p.substring(dotix + 1)
        }
        ret = o && o[p]
    }
    return ret
}


function getfunc(fname) {
    return ((typeof(this[fname]) == "function") && this[fname]) ||
           ((typeof(com.sweattrails.api[fname]) == "function") && com.sweattrails.api[fname])
}

function getChildrenByTagNameNS(elem, ns, tagname) {
    var ret = []
    for (var ix = 0; ix < elem.childNodes.length; ix++) {
        var c = elem.childNodes[ix]
        if ((c.namespaceURI == ns) && (c.localName == tagname)) ret.push(c)
    }
    return ret
}

com.sweattrails.api.renderObject = function(elem, content) {
    if ((typeof(content) == "object") && (typeof(content.render) == "function")) {
        content = content.render()
    }
    if (typeof(content) == "string") {
        elem.innerHTML = content
    } else if (content == null) {
        elem.innerHTML = "&#160;"
    } else {
        elem.appendChild(content)
    }
}

/*
 * MAYBE MOVE ME
 */

function login_error(errorinfo) {
	if (errorinfo != "401") return false
	this.header.error("Mistyped email or password")
	this.footer.error()
	return true
}



/*
 * MOVE ME MOVE ME
 */

var units = [ "metric", "imperial "]
var native_unit = "metric"

function metric() { return (native_unit == "m") }
function imperial() { return (native_unit == "i") }

function rpad(num, width) {
    var n = num + ""
    while (n.length < 2) n = "0" + n
    return n
}

var units_table = {
    distance: { m: 'km', i: 'mile',           factor_i: 0.621371192, factor_m: 1.0 },
    speed:    { m: 'km/h', i: 'mph',          factor_i: 0.621371192, factor_m: 1.0 },
    pace:     { m: 'min/km', i:	'min/mile' },
    length:   { m: 'cm', i: 'in',             factor_i: 0.393700787, factor_m: 1.0 },
    weight:   { m: 'kg', i: 'lbs',            factor_i: 2.20462262, factor_m: 1.0 },
    height:   { m: 'm', i: 'ft/in' }
}

function seconds_to_time(secs) {
    var d = new Date(secs * 1000)
    var ret = {
	'hour': d.getUTCHours(),
	'minute': d.getUTCMinutes(),
	'second': d.getUTCSeconds()
    }
    return ret
}

function time_to_seconds(t) {
    return (t != null) ? t.hour * 3600 + t.minute * 60 + t.second : 0
}

function time_after_offset(t, offset) {
    return seconds_to_time(time_to_seconds(t) - offset)
}

function format_distance(value, metric_imperial) {
    if (metric_imperial == null) metric_imperial = native_unit
    if (value == null) value = 0
    var meters = parseInt(value)
    if (metric_imperial.toLowerCase().substr(0,1) == "m") {
	if (meters < 1000) {
	    return meters + " m"
	} else {
	    var km = parseFloat(value) / 1000.0
	    if (km < 10) {
		return km.toFixed(3) + " km"
	    } else if (meters < 100) {
		return km.toFixed(2) + " km"
	    } else {
		return km.toFixed(1) + " km"
	    }
	}
    } else {
	var miles = meters * 0.0006213712;
	if (miles < 100) {
	    return miles.toFixed(3) + " mi"
	} else {
	    return miles.toFixed(2) + " mi"
	}
    }
}

function format_date(d) {
    if (d && (d.year > 0) && (d.month > 0) && (d.day > 0)) {
        return (metric())
            ? rpad(d.day, 2) + "-" + rpad(d.month, 2) + "-" + d.year
            : rpad(d.month, 2) + "/" + rpad(d.day, 2) + "/" + d.year
    } else {
        return null
    }
}

function format_time(d) {
    if (imperial()) {
        var ampm = ((d.hour < 12) && "am") || "pm"
        return rpad(((d.hour < 13) && d.hour) || (d.hour - 12), 2)  + ":" + rpad(d.minute, 2) + ampm
    } else {
        return rpad(d.hour, 2)  + ":" + rpad(d.minute, 2)
    }
}

function format_datetime(value, format) {
   return format_date(value) + " " + format_time(value)
}

function prettytime(value) {
    if (value == null) value = new Date(0)
    ret = ""
    if (value.hour > 0) {
	ret = value.hour + "hr "
    }
    if (value.minute > 0) {
	ret += value.minute + "min "
    }
    ret += value.second + "s"
    return ret
}

function unit(which, metric_imperial) {
    if (metric_imperial == null) metric_imperial = native_unit
    return units_table[which][metric_imperial.toLowerCase().substr(0,1)]
}

function speed_ms_to_unit(spd, metric_imperial) {
    if (metric_imperial == null) metric_imperial = native_unit
    kmh = spd * 3.6
    if (metric_imperial.toLowerCase().substr(0,1) = 'm') {
	return kmh
    } else {
	return kmh*0.6213712
    }
}

function speed(spd_ms, metric_imperial, include_unit) {
    if (include_unit == null) include_unit = true
    if (metric_imperial == null) metric_imperial = native_unit
    spd = speed_ms_to_unit(spd_ms, metric_imperial)
    ret = spd.toFixed(2)
    if (include_unit) {
	ret += " " + unit('speed', metric_imperial)
    }
    return ret
}

function avgspeed(distance, t, metric_imperial, include_unit) {
    if (include_unit == null) include_unit = true
    if (metric_imperial == null) metric_imperial = native_unit
    seconds = 3600*t.hour + 60*t.minute + t.second
    return speed(distance / seconds, metric_imperial, include_unit)
}

function pace(speed_ms, metric_imperial, include_unit) {
    if (include_unit == null) include_unit = true
    if (metric_imperial == null) metric_imperial = native_unit
    spd = speed_ms_to_unit(speed_ms, metric_imperial, false)
    p = 60 / spd;
    pmin = p.toFixed();
    psec = ((p - pmin) * 60).toFixed();
    ret = pmin + ":"
    if (psec < 10) {
	ret += "0"
    }
    ret += psec
    if (include_unit) {
	ret += " " + unit("pace", metric_imperial)
    }
    return ret
}

function avgpace(distance, t, metric_imperial, include_unit) {
    if (include_unit == null) include_unit = true
    if (metric_imperial == null) metric_imperial = native_unit
    seconds = 3600*t.hour + 60*t.minute + t.second
    return pace(distance/seconds, metric_imperial, include_unit)
}

function convert(metric_value, what, units, include_unit, digits) {
    if (digits == null) digits = 2
    if (include_unit == null) include_unit = true
    factor = units_table[what]['factor_' + units.toLowerCase().substr(0,1)]
    ret = (metric_value * factor).toFixed(digits)
    if (include_unit) {
	ret += " " + unit(what, units)
    }
    return ret
}

function to_metric(value, what, units) {
    if (units == null) units = native_unit
    if ((value != null) && (value != '')) {
	factor = 1.0 / units_table[what]['factor_' + units.toLowerCase().substr(0,1)]
	return parseFloat(value) * factor
    } else {
	return 0.0
    }
}

function length(len_in_cm, units, include_unit) {
    if (include_unit == null) include_unit = true
    if (units == null) units = native_unit
    return convert(parseFloat(len_in_cm), 'length', units, include_unit, 0)
}

function weight(weight_in_kg, units, include_unit) {
    if (include_unit == null) include_unit = true
    if (units == null) units = native_unit
    return convert(parseFloat(weight_in_kg), 'weight', units, include_unit, 0)
}

function distance(distance_in_km, units, include_unit) {
    if (include_unit == null) include_unit = true
    if (units == null) units = native_unit
    return convert(parseFloat(distance_in_km), 'distance', units, include_unit, 2)
}

function height(height_in_cm, units, include_unit) {
    if (include_unit == null) include_unit = true
    if (units == null) units = native_unit
    height_in_cm = parseFloat(height_in_cm)
    if (units.toLowerCase().substr(0,1) == 'm') {
	h = (height_in_cm / 100).toFixed(2)
	if (include_units) {
	    h += ' ' + unit('height', units)
	}
	return h
    } else {
	h_in = Math.round(height_in_cm * 0.393700787)
	ft = Math.floor(h_in / 12)
	inches = h_in % 12
	ret = ''
	if (ft > 0) {
	    ret = ft + "' "
	}
	ret += inches + '"'
	return ret
    }
}

function getXmlHttpRequest() {
    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        httpRequest = new XMLHttpRequest();
    } else if (window.ActiveXObject) { // IE
        try {
            httpRequest = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try {
                httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (e) {}
        }
    }

    if (!httpRequest) {
        alert('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    return httpRequest;
}

function import_file(url, callback) {
    // Brute-force XSS denial:
    if (url.indexOf("http://") === 0) return

    var head = document.getElementsByTagName('head')[0];
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = url;

    if (typeof(callback) == "function") {
	script.onreadystatechange = callback;
	script.onload = callback;
    }

    head.appendChild(script);
}


// ------------------------------------------------------------------------

