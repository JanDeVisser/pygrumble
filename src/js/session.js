var session = null
var waypoints = null
var session_id = "{{sid}}"

var tabdefs = [
    new ST.BasicTab('summary', 'Summary'),
    new IntervalsTab(),
    new GraphsTab(),
    new ST.BasicTab('gear', 'Gear'),
    new MapTab(),
    new RawTab()
]

function getSession(resume) {
    if (session == null) {
	var req = new ST.JSONRequest('/json/session?id=' + encodeURIComponent(session_id),
	    function(obj) {
		session = obj
		resume()
	    })
	req.execute()
    } else {
        resume()
    }
    return true
}

function getWaypoints(resume) {
    if (waypoints == null) {
	var req = new ST.JSONRequest('/json/waypoints?id=' + encodeURIComponent(session_id),
	    function(obj) {
		waypoints = obj
		resume()
	    })
	req.execute()
    } else {
        resume()
    }
    return true
}

function getData(resume) {
    getSession(function() { getWaypoints(resume) })
}

function addDetailRow(table, label) {
    var tr = document.createElement("tr")
    var labelCell = document.createElement("td")
    labelCell.width = "25%"
    labelCell.innerHTML = label + ":"
    tr.appendChild(labelCell)
    for (var i = 2; i < arguments.length; i++) {
	var dataCell = document.createElement("td")
	dataCell.innerHTML = arguments[i]
	tr.appendChild(dataCell)
	table.appendChild(tr)
    }
}

function addDetailHeader(table, header) {
    var tr = document.createElement("tr")
    var headerCell = document.createElement("td")
    headerCell.colspan = 2
    headerCell.innerHTML = "<b>" + header + "</b>"
    tr.appendChild(headerCell)
    table.appendChild(tr)
}

function addBox(page, title) {
    var page = document.getElementById("page_" + page)
    var box = document.createElement("div")
    box.className = "pagebox"
    page.appendChild(box)
    var t = document.createElement("div")
    t.className = "boxtitle"
    t.innerHTML = title
    box.appendChild(t)
    return box
}

function addTable(box, id) {
    var table = document.createElement("table")
    table.width = "100%"
    table.id = id
    box.appendChild(table)
    return table
}

function fillBikeDetails(details) {
    addDetailRow(details, "Average speed", session.interval.average_speed + " " + unit('speed'))
    if (session.interval.max_speed > 0) {
	addDetailRow(details, "Maximum speed", session.interval.max_speed + " " + unit('speed'))
    }
    if (session.interval.average_power > 0) {
	addDetailRow(details, "Average power", session.interval.average_power + " W")
    }
    if (session.interval.normalized_power > 0) {
	addDetailRow(details, "Normalized power", session.interval.normalized_power + " W")
    }
    if (session.interval.max_power > 0) {
	addDetailRow(details, "Maximum power", session.interval.max_power + " W")
    }
    if (session.interval.average_cadence > 0) {
	addDetailRow(details, "Average cadence", session.interval.average_cadence + " rpm")
    }
    if (session.interval.max_cadence > 0) {
	addDetailRow(details, "Maximum cadence", session.interval.max_cadence + " rpm")
    }
    if (session.interval.average_torque > 0) {
	addDetailRow(details, "Average torque", session.interval.average_torque.toFixed(2) + " Nm")
    }
    if (session.interval.max_torque > 0) {
	addDetailRow(details, "Maximum torque", session.interval.max_torque.toFixed(2) + " Nm")
    }

    if (session.interval.critical_power[0]) {
	criticalPowerGraph()
    }
}

function criticalPowerGraph() {
    var page = document.getElementById("page_summary")
    var box = addBox("summary", "Critical Power")
    var canvas = document.createElement("canvas");
    canvas.width = 500 // Math.min(page.offsetWidth - 50, 500)
    canvas.height = 300
    canvas.id = "cp_canvas"
    box.appendChild(canvas)
    var ctx = canvas.getContext('2d')
    if (ctx) {
	var maxpower = session.interval.max_power
	var maxtime = 0
	var timesteps = 0
	for (i in session.interval.critical_power) {
	    cp = session.interval.critical_power[i]
	    if (cp.duration < session.interval.seconds) {
		maxtime = Math.max(cp.duration, maxtime)
		maxpower = Math.max(maxpower, cp.best)
		timesteps++
	    }
	}
	if (maxpower <= 100) {
	    maxpower = 100
	} else if (maxpower <= 200) {
	    maxpower = 200
	} else if (maxpower <= 300) {
	    maxpower = 300
	} else if (maxpower <= 400) {
	    maxpower = 400
	} else if (maxpower <= 500) {
	    maxpower = 500
	} else if (maxpower <= 1000) {
	    maxpower = 1000
	} else if (maxpower <= 1500) {
	    maxpower = 1500
	} else {
	    maxpower = 2000
	}
	var powerstep = maxpower / 5
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	var gw = canvas.width
	var gh = canvas.height
	var maxx = gw - 80
	var maxy = gh - 80

	ctx.beginPath()
	ctx.strokeStyle = "#000000"
	ctx.moveTo(40, 40)
	ctx.lineTo(40, gh - 37)
	ctx.lineTo(gw - 40, gh - 40)
	ctx.stroke()

	var sx = maxx / (timesteps - 1)
	var sy = maxy / maxpower
	var ytick = powerstep
	while (ytick <= maxpower) {
	    ctx.beginPath()
	    ctx.moveTo(37, gh - 40 - sy*ytick)
	    ctx.lineTo(40, gh - 40 - sy*ytick)
	    ctx.textAlign = "right"
	    ctx.strokeText(ytick, 36, gh - 40 - sy*ytick)
	    ctx.stroke()
	    ytick += powerstep
	}
	var xtick = 0
	for (i in session.interval.critical_power) {
	    cp = session.interval.critical_power[i]
	    if (cp.duration < session.interval.seconds) {
		var ticklabel = ""
		if (cp.duration < 60) {
		    ticklabel = cp.duration + "s"
		} else {
		    ticklabel = (cp.duration / 60) + "m"
		}
		cp.xtick = xtick
		ctx.beginPath()
		ctx.strokeStyle = "#000000"
		ctx.moveTo(40 + sx * xtick, gh - 40)
		ctx.lineTo(40 + sx * xtick, gh - 37)
		ctx.textAlign = "center"
		ctx.strokeText(ticklabel, 40 + sx * xtick, gh - 20)
		ctx.stroke()
		if (xtick > 0) {
		    ctx.beginPath()
		    ctx.strokeStyle = "#FF0000"
		    ctx.moveTo(40 + sx * xtick, gh - 38 - sy*cp.power)
		    ctx.lineTo(40 + sx * xtick, gh - 42 - sy*cp.power)
		    ctx.stroke()
		    ctx.beginPath()
		    ctx.strokeStyle = "#00FF00"
		    ctx.moveTo(40 + sx * xtick, gh - 38 - sy*cp.best)
		    ctx.lineTo(40 + sx * xtick, gh - 42 - sy*cp.best)
		    ctx.stroke()
		}
		xtick++
	    }
	}
	ctx.beginPath()
	ctx.strokeStyle = "#FF0000"
	//ctx.moveTo(40, gh - 40 - sy*session.interval.max_power)
	for (i in session.interval.critical_power) {
	    cp = session.interval.critical_power[i]
	    if (cp.duration < session.interval.seconds) {
		if (cp.xtick == 0) {
		    ctx.moveTo(40 + sx * cp.xtick, gh - 40 - sy*cp.power)
		} else {
		    ctx.lineTo(40 + sx * cp.xtick, gh - 40 - sy*cp.power)
		}
	    }
	}
	ctx.stroke()
	ctx.beginPath()
	ctx.strokeStyle = "#00FF00"
	//ctx.moveTo(40, gh - 40 - sy*session.interval.max_power)
	for (i in session.interval.critical_power) {
	    cp = session.interval.critical_power[i]
	    if (cp.duration < session.interval.seconds) {
		if (cp.xtick == 0) {
		    ctx.moveTo(40 + sx * cp.xtick, gh - 40 - sy*cp.best)
		} else {
		    ctx.lineTo(40 + sx * cp.xtick, gh - 40 - sy*cp.best)
		}
	    }
	}
	ctx.stroke()
    }
    var cptable = addTable(box, "critical_power")
    for (var i in session.interval.critical_power) {
	var cp = session.interval.critical_power[i]
	addDetailRow(cptable, cp.label, cp.power + " W", prettytime(seconds_to_time(cp.timestamp)))
    }
}

function fillRunDetails(details) {
    addDetailRow(details, "Average pace", session.interval.average_pace + " " + unit('pace'))
    addDetailRow(details, "Best pace", session.interval.best_pace + " " + unit('pace'))
}

function fillDetails(obj) {
    session = obj
    var st_img = document.getElementById("sessiontype")
    st_img.src = '/images/' + session.interval.type + ".png"
    var descr = document.getElementById("description")
    if (session.description != "") {
	descr.innerHTML = session.description
    } else {
	descr.innerHTML = "<i>No description</i>"
    }
    var summary = document.getElementById('summarytable')
    addDetailRow(summary, "Started", format_datetime(session.start))
    addDetailRow(summary, "Posted", format_datetime(session.posted))
    addDetailRow(summary, "Activity", session.sessiontype)
    addDetailRow(summary, "Distance", format_distance(session.interval.distance))
    addDetailRow(summary, "Time", prettytime(seconds_to_time(session.interval.seconds)))
    var details = document.getElementById('detailstable')
    if (session.interval.type == 'bike') {
	fillBikeDetails(details)
    } else if (session.interval.type == 'run'){
	fillRunDetails(details)
    }
    if (session.interval.avg_hr > 0) {
	addDetailRow(details, "Average heartrate", session.interval.average_hr + " bpm")
    }
    if (session.interval.max_hr > 0) {
	addDetailRow(details, "Maximum heartrate", session.interval.max_hr + " bpm")
    }
    var notes = document.getElementById("notes")
    if (notes.description != "") {
	notes.innerHTML = session.notes
    } else {
	notes.innerHTML = "&#160;"
    }
}

function onPagePreLoad() {
    var req = new ST.JSONRequest('/json/session?id=' + encodeURIComponent(session_id), fillDetails)
    req.async = false
    req.execute()
}

function Plot(id, label, color, max, avg) {
    this.id = id
    this.label = label
    this.color = color
    this.max = max
    this.avg = avg
}

function PlotContext(canvas) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    this.plots = new Object()
}

PlotContext.prototype.reset = function() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);	
    this.gw = this.canvas.width
    this.gh = this.canvas.height
    this.maxx = this.gw - 80
    this.maxy = this.gh - 80

    this.ctx.beginPath()
    this.ctx.strokeStyle = "#000000"
    this.ctx.moveTo(40, 40)
    this.ctx.lineTo(40, this.gh - 40)
    this.ctx.lineTo(this.gw - 40, this.gh - 40)
    this.ctx.lineTo(this.gw - 40, 40)
    this.ctx.stroke()
}

PlotContext.prototype.addplot = function(plot) {
    if (typeof(this.plots[plot.id]) == 'undefined') {
	this.plots[plot.id] = plot
	var s = document.getElementById('plot_selector')
	var lbl = document.createElement("label")
	s.appendChild(lbl)
	var cb = document.createElement('input')
	cb.type = 'checkbox'
	cb.value = plot.id
	cb.defaultChecked = true
	cb.checked = true
	cb.id = 'cb-' + plot.id
	cb.onclick = redraw
	lbl.appendChild(cb)
	var span = document.createElement("span")
	span.style.color = plot.color
	span.innerHTML = "&#160;" + plot.label + "&#160;"
	lbl.appendChild(span)
    }
}

PlotContext.prototype.plot = function () {
    this.smoothing = parseInt(document.getElementById("smoothing").value)
    for(var pid in this.plots) {
	var p = this.plots[pid]
	cb = document.getElementById('cb-' + pid)
	if (cb.checked) {
	    this.plotIt(p)
	}
    }
}

PlotContext.prototype.plotIt = function(plot) {
    var ctx = this.ctx
    var sx = this.maxx / session.interval.seconds;
    var sy = this.maxy / plot.max;
    ctx.beginPath()
    var moved = false
    ctx.strokeStyle = plot.color
    var n = 0
    var t = 0
    var sum = 0
    var pt = 0
    for (var ix = 0; ix < waypoints.length; ix++) {
        var d = waypoints[ix]
    	var v = plot.data(d)
        if (ix == 0) {
	    t = d.seconds
	    n = 1
	    sum = v
	    pt = d.seconds
        } else {
	    if (d.seconds > (t + this.smoothing)) {
		var x = 40 + sx*pt
		var y = this.gh - 40 - sy*(sum/n)
		if (!moved) {
		    ctx.moveTo(x,y)
		    moved = true
		} else {
		    ctx.lineTo(x,y)
		}
		t = d.seconds
		n = 1
		sum = v
		pt = d.seconds
	    } else {
		n++;
		sum += v
		pt = d.seconds
	    }
        }
    }
    ctx.moveTo(40, this.gh - 40 - sy*plot.avg)
    ctx.lineTo(this.gw - 40, this.gh - 40 - sy*plot.avg)
    ctx.textAlign = "right"
    ctx.strokeText(plot.avg, 38, this.gh - 40 - sy*plot.avg)
    ctx.stroke()
}

var myctx = null

function GraphsTab() {
    this.code = "graphs"
    this.label = "Graphs"
    this.onSelect = function() {
	var page = document.getElementById("page_graphs");
	var canvas = document.getElementById('canvas')
	if (canvas == null) {
	    canvas = document.createElement("canvas");
	    canvas.width = page.offsetWidth - 50
	    canvas.height = window.innerHeight - page.offsetTop - 150
	    canvas.id = "graphs"
	    page.appendChild(canvas)
	    if (!canvas.getContext) {
		alert("Your browser does not support graphs");
		return;
	    }
	}
	redraw();
    }
    return this
}
    
function redraw() {
    getSession(_redraw)
}

function _redraw() {
    if (myctx == null) {
        myctx = new PlotContext(document.getElementById("graphs"))
    }
    myctx.reset()
    getWaypoints(__redraw)
}

function __redraw() {
    if (session.interval.max_power > 0) {
        powerplot = new Plot("power", "Power", "#ff0000", session.interval.max_power, session.interval.average_power)
        powerplot.data = function(wp) { return wp.power }
        myctx.addplot(powerplot)
    }
    
    if (session.interval.max_cadence > 0) {
        cadenceplot = new Plot("cadence", "Cadence", "#00ff00", session.interval.max_cadence, session.interval.average_cadence)
        cadenceplot.data = function(wp) { return wp.cadence }
        myctx.addplot(cadenceplot)
    }
    
    if (session.interval.max_speed > 0) {
        speedplot = new Plot("speed", "Speed", "#0000ff", session.interval.max_speed, session.interval.average_speed)
        speedplot.data = function(wp) { return wp.speed }
        myctx.addplot(speedplot)
    }
    
    if (session.interval.max_torque > 0) {
        torqueplot = new Plot("torque", "Torque", "#ff00ff", session.interval.max_torque, session.interval.average_torque)
        torqueplot.data = function(wp) { return wp.speed }
        myctx.addplot(torqueplot)
    }
    
    if (session.interval.max_hr > 0) {
        hrplot = new Plot("hr", "Heartrate", "#00ffff", session.interval.max_hr, session.interval.average_hr)
        hrplot.data = function(wp) { return wp.heartrate }
        myctx.addplot(hrplot)
    }
    
    myctx.plot()
}

function IntervalsTab() {
    this.label = "Intervals"
    this.code = "intervals"
    this.count = 0
    return this
}

IntervalsTab.prototype.onDraw = function() {
    return session.interval.num_intervals > 1
}

IntervalsTab.prototype.onSelect = function() {
    if (this.table == null) {
        var page = document.getElementById("page_intervals")
        this.table = new ST.Table(page, "interval", this)
        this.table.addColumns(
            new ST.Column("#", function(interval) { return interval.interval_id + 1 }),
            new ST.Column("Time", function(interval) { return prettytime(seconds_to_time(interval.seconds)) }),
            new ST.Column("Distance", function(interval) { return format_distance(interval.distance) }))
        if (session.interval.type == 'bike') {
            this.bikeIntervals()
        } else {
            this.runIntervals()
        }
        this.table.populate()
    }
}

IntervalsTab.prototype.next = function() {
    if (this.count < session.interval.intervals.length) {
        var ret = session.interval.intervals[this.count++]
        return ret
    } else {
        return null
    }
}

IntervalsTab.prototype.bikeIntervals = function() {
    if (session.interval.max_power > 0) {
        this.table.addColumns(
            new ST.Column("Power", function(interval) { return interval.average_power }),
            new ST.Column("NP", function(interval) { return interval.normalized_power }),
            new ST.Column("Max. Power", function(interval) { return interval.max_power }))
    }
    if (session.interval.max_hr > 0) {
        this.table.addColumns(
            new ST.Column("HR", function(interval) { return interval.average_hr }),
            new ST.Column("Max. HR", function(interval) { return interval.max_hr }))
    }
    if (session.interval.max_speed > 0) {
        this.table.addColumns(
            new ST.Column("Speed", function(interval) { return interval.average_speed }),
            new ST.Column("Max. Speed", function(interval) { return interval.max_speed }))
    }
    if (session.interval.max_cadence > 0) {
        this.table.addColumns(
            new ST.Column("Cadence", function(interval) { return interval.average_cadence }),
            new ST.Column("Max. Cadence", function(interval) { return interval.max_cadence }))
    }
    if (session.interval.max_torque > 0) {
        this.table.addColumns(
            new ST.Column("Torque", function(interval) { return interval.average_torque }),
            new ST.Column("Max. Torque", function(interval) { return interval.max_torque }))
    }
}

IntervalsTab.prototype.runIntervals = function() {
    if (session.interval.max_speed > 0) {
        this.table.addColumns(
            new ST.Column("Pace", function(interval) { return interval.average_pace }),
            new ST.Column("Best Pace", function(interval) { return interval.best_pace }))
    }
    if (session.interval.max_hr > 0) {
        this.table.addColumns(
            new ST.Column("HR", function(interval) { return interval.average_hr }),
            new ST.Column("Max. HR", function(interval) { return interval.max_hr }))
    }
    if (session.interval.max_cadence > 0) {
        this.table.addColumns(
            new ST.Column("Cadence", function(interval) { return interval.average_cadence }),
            new ST.Column("Max. Cadence", function(interval) { return interval.max_cadence }))
    }
}

function MapTab() {
    this.label = "Map"
    this.code = "map"
    this.onDraw = function() {
	if ((typeof(session.interval.geodata) == 'undefined') ||
	    (typeof(session.interval.geodata.max_ne) == 'undefined') ||
	    (session.interval.geodata.max_ne.lat >= 200)) {
	    return false
	} else {
	    return true
	}
    }
    this.onSelect = function() {
	getSession(selectMap)
    }
    return this
}

function selectMap() {
    var geodata = session.interval.geodata
    session.ne_loc = new google.maps.LatLng(geodata.max_ne.lat, geodata.max_ne.lon)
    session.sw_loc = new google.maps.LatLng(geodata.max_sw.lat, geodata.max_sw.lon)
    session.center_loc = new google.maps.LatLng((geodata.max_ne.lat + geodata.max_sw.lat)/2, (geodata.max_ne.lon + geodata.max_sw.lon)/2);
    bounds = new google.maps.LatLngBounds(session.sw_loc, session.ne_loc)
    options = {
        zoom: 12,
        center: session.center_loc,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    map = new google.maps.Map(document.getElementById("map_canvas"), options);
    map.fitBounds(bounds)
    getWaypoints(__selectMap)
}

function __selectMap() {	
    wps = new Array();
    wp_html = new Array();
    for (i = 0; i < waypoints.length; i++) {
        wp = waypoints[i]
        if (wp.location.lat < 200) {
	    wp.coords = new google.maps.LatLng(wp.location.lat, wp.location.lon)
	    wps.push(wp.coords)
        } else {
	    wp.coords = null
        }
    }
    var path = new google.maps.Polyline({
        path: wps,
        strokeColor: "#FF0000",
        strokeOpacity: 1.0,
        strokeWeight: 2
    });
    path.setMap(map);
}

function RawTab() {
    this.code = "raw"
    this.label = "Raw data"
    this.onSelect = function() {
	getData(selectRaw)
    }
    return this
}

function addTD(tr, txt) {
    td = document.createElement('td')
    td.innerHTML = txt
    tr.appendChild(td)
}

function createWaypointRow(wp) {
    tr = document.createElement('tr')
    addTD(tr, wp.seqnr)
    addTD(tr, wp.seconds + " sec")
    addTD(tr, wp.distance + " m")
    addTD(tr, wp.power + " W")
    addTD(tr, wp.speed + " km/h")
    addTD(tr, wp.torque + " Nm")
    addTD(tr, wp.heartrate + " bpm")
    addTD(tr, wp.cadence + " rpm")
    addTD(tr, wp.altitude + " m")
    if (wp.location.lat >= 200) {
        addTD(tr, "&#160;")
    } else {
        addTD(tr, wp.location.lat + "/" + wp.location.lon)
    }
    return tr
}

function selectRaw() {
    table = document.getElementById('raw_table')
    color = 'white'
    for (ix = 0; ix < waypoints.length; ix++) {
        wp = waypoints[ix]
        tr = createWaypointRow(wp)
        tr.style.backgroundColor = color
        if (color == 'white') {
	    color = 'lightblue' 
        } else {
	    color = 'white'
        }
        table.appendChild(tr)
    }
}

