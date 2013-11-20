/* 
 * (c) 2012-2014 finiandarcy.com under the BSD license.
 */

com.sweattrails.api.Graph = function(id, container) {
    this.container = container;
    this.id = id;
    this.type = "graph";
    com.sweattrails.api.STManager.register(this);
    this.canvas = null;
    if (arguments.length > 2) {
        this.setDataSource(arguments[2]);
    }
    this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
    this.header = new com.sweattrails.api.ActionContainer(this, "header");
    this.plots = {};
    return this;
};

com.sweattrails.api.Graph.prototype.reset = function() {
    $$.log(this, "Graph.initialize");
    this.header.erase();
    this.footer.erase();
    this.header.render();
    if (!this.canvas) {
        this.canvas = document.createElement("canvas");
        this.canvas.width = this.container.innerWidth;
        this.canvas.height = this.container.innerHeight;
        this.canvas.id = this.id + "-canvas";
        this.container.appendChild(this.canvas);
        if (!canvas.getContext) {
            alert("Your browser does not support graphs");
            return;
        }
        this.ctx = this.canvas.getContext('2d');
    } else {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);	
        this.gw = this.canvas.width;
        this.gh = this.canvas.height;
        this.maxx = this.gw - 80;
        this.maxy = this.gh - 80;

        this.ctx.beginPath();
        this.ctx.strokeStyle = "#000000";
        this.ctx.moveTo(40, 40);
        this.ctx.lineTo(40, this.gh - 40);
        this.ctx.lineTo(this.gw - 40, this.gh - 40);
        this.ctx.lineTo(this.gw - 40, 40);
        this.ctx.stroke();
    }
};

com.sweattrails.api.Graph.prototype.addPlot = function(plot) {
    if (typeof(this.plots[plot.id]) === 'undefined') {
	this.plots[plot.id] = plot;
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




