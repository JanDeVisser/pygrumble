/*
 * Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
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
 * Axis -
 */

com.sweattrails.api.internal.GraphConverter = {}
com.sweattrails.api.internal.GraphConverter.number = parseFloat;
com.sweattrails.api.internal.GraphConverter.time = timeobj_to_seconds;
com.sweattrails.api.internal.GraphConverter.pace = function(speed_ms) { return pace_as_number(speed_ms, "metric"); };

com.sweattrails.api.Axis = function () {
    this.bridge = new com.sweattrails.api.internal.DataBridge();
    this.bwbridge = null;
    this.clear();
}

com.sweattrails.api.Axis.prototype.setProperty = function (prop) {
    if (prop === "#") {
        prop = function (object, axis) {
            return axis.coordinates.length;
        };
    }
    this.bridge.get = prop;
};

com.sweattrails.api.Axis.prototype.setType = function (type) {
    this.converter = com.sweattrails.api.internal.GraphConverter[type];
    if (typeof(this.converter) === 'undefined') {
        this.converter = com.sweattrails.api.internal.GraphConverter["number"];
    }
};

com.sweattrails.api.Axis.prototype.setDecorator = function (decorator) {
    if (!decorator) return;
    switch (typeof(decorator)) {
        case "string":
            this.decorator = __.getfunc(decorator);
            break;
        case "function":
            this.decorator = decorator;
            break;
        default:
            throw new __.TypeError("Attempt to use object of type %s as decorator", typeof(decorator));
    }
};

com.sweattrails.api.Axis.prototype.build = function(elem) {
    this.set(elem, "type", this.setType);
    this.set(elem, "decorate", this.setDecorator)
    this.set(elem, "ticks", null, com.sweattrails.api.BuilderFlags.Function);
    this.set(elem, "tickscale", null, com.sweattrails.api.BuilderFlags.Function);
    this.set(elem, "unit", null, com.sweattrails.api.BuilderFlags.Function);
    this.set(elem, "grid", null, com.sweattrails.api.BuilderFlags.Boolean);
}

com.sweattrails.api.Axis.prototype.clear = function () {
    this.coordinates = [];
    this.min = NaN;
    this.max = NaN;
    this.range = NaN;
};

com.sweattrails.api.Axis.prototype.getCoordinateValue = function (bridge, object) {
    var v = bridge.getValue(object, this);
    // $$.log(this, "v: %s converter: %s", v, this.converter);
    v = (typeof(this.converter) === 'function') ? this.converter(v) : parseFloat(v);
    // $$.log(this, "Converted: %s", v);

    if (isNaN(this.max) || (v > this.max)) {
        this.max = v;
        if (!isNaN(this.min) && (this.max !== this.min)) {
            this.range = this.max - this.min;
        }
    }
    if (isNaN(this.min) || (v < this.min)) {
        this.min = v;
        if (!isNaN(this.max) && (this.max !== this.min)) {
            this.range = this.max - this.min;
        }
    }
    return v;
};

com.sweattrails.api.Axis.prototype.getCoordinate = function (object) {
    this.coordinates.push(this.getCoordinateValue(this.bridge, object));
};

com.sweattrails.api.Axis.prototype.decorate = function (column) {
    if (this.decorator) {
        this.decorator();
    } else {
        var g = this.graph;
        var p = g.pad;
        var ctx = g.ctx;
        var x = NaN, y = NaN, xaxis = false;
        if (column === 0) {
            ctx.textAlign = "center";
            y = this.gh - (p.bottom - 20);
            xaxis = true;
        } else if (column < 0) {
            ctx.textAlign = "right";
            x = p.left - 2 + 20 * (column + 1);
        } else {
            ctx.textAlign = "left";
            x = g.gw - p.right + 2 + 20 * (column - 1);
        }
        ctx.save();
        ctx.strokeStyle = this.color;
        ctx.lineWidth = 1;
        var ticks;
        if (typeof(this.ticks) === "function") {
            ticks = this.ticks();
            $$.log(this, "ticks function returns %s (%s %s)", ticks, typeof(ticks), Array.isArray(ticks));
        } else if (this.ticks) {
            ticks = [];
            ticks = this.ticks.split(",").forEach(function (t) { ticks.push(parseFloat(t)); });
        } else if (this.tickscale) {
            var scale = (typeof(this.tickscale) === "function") ? this.tickscale() : parseFloat(this.tickscale);
            ticks = [];
            for (var t = Math.ceil((this.min - 0.5*this.range) / scale) * scale;
                 t < (this.max + 0.5 * this.range); t += scale) {
                ticks.push(t);
                t += scale;
            }
        } else {
            ticks = [ this.min, this.max ];
        }
        ticks.forEach(function(t, ix) {
                if (typeof(t) !== "object") {
                    t = {value: t, label: t.toString()};
                    ticks[ix] = t;
                }
                var v = t.value;
                if (typeof(v) !== "number") {
                    v = v + "";
                    v = (v.indexOf(v, ".") >= 0) ? parseFloat(v) : parseInt(v);
                    t.value = v;
                }
            });
        ticks.sort(function(t1, t2) {
            return t1.value - t2.value;
        });
        $$.log(this, "ticks %s (%s %s)", ticks, typeof(ticks), Array.isArray(ticks));
        var prev = NaN;
        for (var ix = 0; ix < ticks.length; ix++) {
            var tick = ticks[ix];
            var xc = (!xaxis) ? x : this.toCanvasXCoordinate(tick.value);
            var yc = (xaxis) ? y : this.toCanvasYCoordinate(tick.value);
            var cur = (xaxis) ? xc : -yc;
            if (!isNaN(prev) && ((cur - prev) < 15)) {
                $$.log(this, "Skipping tick: value: %f x: %d xc: %d y: %d yc: %d lbl: %s",
                    tick.value, x, xc, y, yc, tick.label);
                continue;
            } else {
                $$.log(this, "Drawing tick: value: %f x: %d xc: %d y: %d yc: %d lbl: %s",
                    tick.value, x, xc, y, yc, tick.value);
            }

            prev = cur;
            ctx.strokeText(tick.label, xc, yc);

            if (this.grid || tick.grid) {
                ctx.save();
                ctx.setLineDash([7, 5]);
                ctx.moveTo((!xaxis) ? p.left : xc, (xaxis) ? g.gh - p.bottom : yc);
                ctx.lineTo((!xaxis) ? (g.gw - p.right) : xc, (xaxis) ? p.top : yc);
                ctx.stroke();
                ctx.restore();
            }
        }
        var unit = (this.unit) ? ((typeof(this.unit) === "function") ? this.unit() : this.unit) : "";
        if (unit) {
            ctx.strokeText(unit, (!xaxis) ? x : g.gw - p.right, (xaxis) ? y : p.top);
        }
        ctx.restore();
    }
};

/**
 * Graph -
 */

com.sweattrails.api.Graph = function (container, id) {
    this.series = [];
    this.graph = this;
    com.sweattrails.api.Axis.call(this);
    this.color = "#000000";
    this.hasDataSource = true;
    this.container = document.createElement("div")
    this.container.id = "graph-" + id;
    container.appendChild(this.container);
    this.id = id;
    this.type = "graph";
    this.bwbridge = null;
    this.pad = { left: 40, right: 40, top: 40, bottom: 40 };
    $$.register(this);

    this.pleasewait = document.createElement("div");
    this.pleasewait.id = "graph-pleasewait-" + id;
    var span = document.createElement("span");
    span.style.textAlign = "center";
    var img = document.createElement("img");
    img.src = "/image/throbber.gif";
    img.height = img.width = 32;
    span.appendChild(img);
    span.appendChild(document.createTextNode("\u00A0Please wait"));
    this.pleasewait.appendChild(span);
    this.container.appendChild(this.pleasewait);

    this.controls = document.createElement("div");
    this.container.appendChild(this.controls);
    this.controls.id = "graph-controls-" + this.id;
    //this.controls.hidden = true;
    this.canvas = null;

    this.footer = new com.sweattrails.api.ActionContainer(this, "footer");
    this.header = new com.sweattrails.api.ActionContainer(this, "header");
    return this;
};

com.sweattrails.api.Graph.prototype = new com.sweattrails.api.Axis();

com.sweattrails.api.Graph.prototype.build = function(elem) {
    com.sweattrails.api.Axis.prototype.build.call(this, elem);
    this.set(elem, "height", "height",
        com.sweattrails.api.BuilderFlags.Int | com.sweattrails.api.BuilderFlags.Bind);
    this.set(elem, "width", "width",
        com.sweattrails.api.BuilderFlags.Int | com.sweattrails.api.BuilderFlags.Bind);
    this.set(elem, "left", "pad.left", com.sweattrails.api.BuilderFlags.Int);
    this.set(elem, "right", "pad.right", com.sweattrails.api.BuilderFlags.Int);
    this.set(elem, "top", "pad.top", com.sweattrails.api.BuilderFlags.Int);
    this.set(elem, "bottom", "pad.bottom", com.sweattrails.api.BuilderFlags.Int);
    this.set(elem, "xcoordinate", this.setProperty);
    this.set(elem, "bucketwidth", this.setBucketWidthProperty);
    this.set(elem, "onrender");
    this.set(elem, "onrendered");
    this.set(elem, "onnodata");
    this.buildChildren(elem, "series", com.sweattrails.api.Series);
}

com.sweattrails.api.Graph.prototype.createCanvas = function () {
    if (this.canvas) {
        this.container.removeChild(this.canvas);
        this.canvas = null;
    }
    this.canvas = document.createElement("canvas");
    if (!this.canvas.getContext) {
        alert("Your browser does not support graphs");
        throw new DOMException("Browser does not support graphs");
    }
    this.canvas.id = "graph-" + this.id + "-canvas";
    this.container.appendChild(this.canvas);
    // this.canvas.style.width='100%';
    // this.canvas.style.height='100%';
    //this.canvas.width = this.canvas.style.width;
    //this.canvas.height = this.canvas.style.height;
    if (this.width) {
        this.canvas.width = (typeof(this.width) === "function") ? this.width(this) : this.width;
    }
    if (this.height) {
        this.canvas.height = (typeof(this.height) === "function") ? this.height(this) : this.height;
    }
    $$.log(this, "canvas: %d/%d/%dx%s/%d/%d",
        this.pad.top, this.canvas.height, this.pad.bottom, this.pad.left, this.canvas.width, this.pad.right);
    this.gw = this.canvas.width;
    this.gh = this.canvas.height;
    this.maxx = this.gw - (this.pad.left + this.pad.right);
    this.maxy = this.gh - (this.pad.left + this.pad.right);
    this.ctx = this.canvas.getContext('2d');
    this.ctx.roundedRect = com.sweattrails.api.roundedRect.bind(this.ctx);
    return this.canvas;
};

com.sweattrails.api.Graph.prototype.setBucketWidthProperty = function (bw) {
    this.bwbridge = new com.sweattrails.api.internal.DataBridge(bw);
};

com.sweattrails.api.Graph.prototype.addSeries = function (series) {
    this.series.push(series);
    series.graph = this;
};

com.sweattrails.api.Graph.prototype.reset = function (data) {
    $$.log(this, "Graph.reset");
    this.datasource.reset(data);
    this.render();
};

com.sweattrails.api.Graph.prototype.erase = function () {
    $$.log(this, "erase()");
    this.header.erase();
    this.footer.erase();
    this.pleasewait.hidden = false;
    this.controls.hidden = true;
    if (this.canvas) {
        this.container.removeChild(this.canvas);
        this.canvas = null;
    }
};

com.sweattrails.api.Graph.prototype.render = function () {
    $$.log(this, "render()");
    this.erase();
    this.clear();
    this.datasource.execute();
};

com.sweattrails.api.Graph.prototype.onData = function (data) {
    $$.log(this, "onData");
    this.onrender && this.onrender(data);
    this.header.render();

    this.series.forEach(function (s) {
        s.render();
    });

    this.footer.render();
};

com.sweattrails.api.Graph.prototype.noData = function () {
    $$.log(this, "noData");
    this.pleasewait.hidden = true;
    this.onnodata && this.onnodata();
    if (this.canvas) {
        this.container.removeChild(this.canvas);
        this.canvas = null;
    }
    this.header.erase();
    this.footer.erase();

    this.header.render();
    this.canvas = document.createElement("span");
    this.canvas.id = this.id + "-empty";
    this.canvas.innerHTML = "&#160;<i>No data</i>";
    this.container.appendChild(this.canvas);
    this.footer.render();
};

com.sweattrails.api.Graph.prototype.renderData = function (obj) {
    if (!obj) return;
    // $$.log(this, "Graph.renderData");
    this.getCoordinates(obj);
};

com.sweattrails.api.Graph.prototype.clear = function () {
    com.sweattrails.api.Axis.prototype.clear.call(this);
    this.buckets = [];
    this.series.forEach(function (s) {
        s.clear();
    });
};

com.sweattrails.api.Graph.prototype.getCoordinates = function (object) {
    this.getCoordinate(object);
    if (this.bwbridge) {
        var x = this.coordinates[this.coordinates.length - 1];
        var v = this.getCoordinateValue(this.bwbridge, object);
        var xx = x + v;
        this.buckets.push(v);
        if (isNaN(this.max) || (xx > this.max)) {
            this.max = xx;
            if (!isNaN(this.min) && (this.max !== this.min)) {
                this.range = this.max - this.min;
            }
        }
        // $$.log(this, "Added X coordinates (%d, +%d) max: %d range: %d", x, v, this.max, this.range);
    }
    this.series.forEach(function (s) {
        s.getCoordinate(object);
    });
};

com.sweattrails.api.Graph.prototype.onDataEnd = function () {
    if (isNaN(this.max)) {
        this.noData();
    } else {
        this.plot();
        this.onrendered && this.onrendered();
    }
};

com.sweattrails.api.Graph.prototype.plot = function () {
    this.pleasewait.hidden = true;
    this.controls.hidden = this.series.length <= 1;

    this.createCanvas();
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.strokeStyle = "#000000";
    this.ctx.lineWidth = 2;
    this.ctx.moveTo(this.pad.left, this.pad.top);
    this.ctx.lineTo(this.pad.left, this.gh - this.pad.bottom);
    this.ctx.lineTo(this.gw - this.pad.right, this.gh - this.pad.bottom);
    this.ctx.lineTo(this.gw - this.pad.right, this.pad.top);
    this.ctx.stroke();
    this.ctx.restore();

    this.xscale = this.maxx / this.range;
    $$.log(this, "plot() x.min: %f x.max: %f x.range: %f x.scale: %f",
        this.min, this.max, this.range, this.xscale);
    this.decorate(0);
    this.series.forEach(function (s, ix) {
        /*
         * First one gets index -1, then 1, then -2, then 2, etc. Negative indicates that the scale goes left,
         * positive right.
         */
        s.plot(Math.floor(-1*Math.pow(-1,ix)*((ix+1)/2)));
    });
};

com.sweattrails.api.Graph.prototype.redraw = function () {
    $$.log(this, "redraw()");
    this.erase();
    this.plot();
};

com.sweattrails.api.GraphColors = ["red", "blue", "green", "magenta", "orange", "gray", "black"];

com.sweattrails.api.Graph.prototype.nextColor = function () {
    return com.sweattrails.api.GraphColors[this.series.length - 1];
};

com.sweattrails.api.Graph.prototype.toCanvasXDistance = function(x) {
    return this.xscale * (x - this.min);
};

com.sweattrails.api.Graph.prototype.toCanvasXCoordinate = function(x) {
    return this.pad.left + this.toCanvasXDistance(x);
};

/* Series */

com.sweattrails.api.Series = function (graph) {
    com.sweattrails.api.Axis.call(this);
    this.type = "series";
    if (arguments.length > 1) {
        this.id = arguments[1];
    }
    this.onoff = null;
    graph.addSeries(this);
};

com.sweattrails.api.Series.prototype = new com.sweattrails.api.Axis();

com.sweattrails.api.Series.prototype.build = function (elem) {
    this.id = elem.getAttribute("id") || elem.getAttribute("coordinate");
    com.sweattrails.api.Axis.prototype.build.call(this, elem);
    this.set(elem, "label", function(v) { this.label = v || this.id; });
    this.set(elem, "color", function(v) { this.color = v || this.graph.nextColor(); });
    this.set(elem, "coordinate", this.setProperty);
    this.set(elem, "style",
        function(v) {
            v = v || "Line";
            var plotter = com.sweattrails.api[v.toTitleCase() + "Plot"];
            if (typeof(plotter) !== 'function') {
                plotter = com.sweattrails.api.LinePlot;
            }
            this.plotter = new plotter(this, elem);
        });
};

com.sweattrails.api.Series.prototype.render = function () {
    var g = this.graph;
    if (!this.onoff) {
        this.onoff = document.createElement("label");
        g.controls.appendChild(this.onoff);
        this.cb = document.createElement('input');
        this.cb.type = 'checkbox';
        this.cb.value = self.id;
        this.cb.defaultChecked = true;
        this.cb.checked = true;
        this.cb.id = 'graph-control-' + g.id + "-" + self.id;
        this.cb.onclick = this.graph.redraw.bind(this.graph);
        this.onoff.appendChild(this.cb);
        var span = document.createElement("span");
        span.style.color = this.color;
        span.innerHTML = "&#160;" + this.label + "&#160;";
        this.onoff.appendChild(span);
    }
};

com.sweattrails.api.Series.prototype.plot = function (column) {
    $$.log(this, "plot()");
    if (isNaN(this.min)) {
        this.onoff.hidden = true;
        return;
    }
    if (!this.cb.checked) {
        return;
    }
    this.scale = this.graph.maxy / (this.range * 2);
    $$.log(this, "plot(). y.min: %f y.max: %f y.range: %f y.scale: %f",
        this.min, this.max, this.range, this.scale);
    this.plotter.plot();
    this.decorate(column);
};

com.sweattrails.api.Series.prototype.toCanvasYCoordinate = function (y) {
    var g = this.graph;
    return g.gh - g.pad.bottom - this.scale * (y - (this.min - (this.range / 2)));
};

com.sweattrails.api.Series.prototype.toCanvasCoordinates = function (ix) {
    var g = this.graph;
    return {
        x: g.toCanvasXCoordinate(g.coordinates[ix]),
        y: this.toCanvasYCoordinate(this.coordinates[ix])
    };
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.LinePlot = function(series, elem) {
    com.sweattrails.api.GritObject.mixin(this);
    this.series = series;
    this.set(elem, "fill", null, com.sweattrails.api.BuilderFlags.Boolean);
};

com.sweattrails.api.LinePlot.prototype.plot = function () {
    var g = this.series.graph;
    var ctx = g.ctx;
    ctx.save();
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 2;
    ctx.strokeStyle = this.series.color;
    if (typeof(this.fill) === "string") {
        ctx.fillStyle = this.fill;
    } else if (this.fill) {
        var c = __.getColor(this.series.color);
        c = c.shade(0.7);
        ctx.fillStyle = c.rgb();
    }
    ctx.beginPath();
    var xy;
    for (var ix = 0; ix < g.coordinates.length; ix++) {
        xy = this.series.toCanvasCoordinates(ix);
        if (ix === 0) {
            ctx.moveTo(xy.x, xy.y);
        } else {
            ctx.lineTo(xy.x, xy.y);
        }
    }
    if (this.fill) {
        ctx.lineTo(xy.x, g.gh - g.pad.bottom);
        ctx.lineTo(g.pad.left, g.gh - g.pad.bottom);
        ctx.closePath();
        ctx.fill();
    }
    ctx.stroke();
    ctx.restore();
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.BarPlot = function(series) {
    this.series = series;
};

com.sweattrails.api.BarPlot.prototype.plot = function () {
    var g = this.series.graph;
    var ctx = g.ctx;
    ctx.save();
    ctx.strokeStyle = this.series.color;
    var c = __.getColor(this.series.color);
    c = c.shade(0.7);
    ctx.fillStyle = c.rgb();
    var ybase = g.gh - g.pad.bottom;
    for (var ix = 0; ix < g.coordinates.length; ix++) {
        var xy = this.series.toCanvasCoordinates(ix);
        var bucketwidth = g.toCanvasXDistance(g.buckets[ix]);
        // $$.log(this, "(%d+%d,%d+%d)", xy.x, bucketwidth, xy.y, ybase - xy.y);
        ctx.roundedRect(xy.x, xy.y, bucketwidth, ybase - xy.y, 5, true);
    }
    ctx.restore();
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.ScatterPlot = function(series) {
    this.series = series;
};

com.sweattrails.api.ScatterPlot.prototype.plot = function () {
    var g = this.series.graph;
    var ctx = g.ctx;
    ctx.save();
    ctx.fillStyle = this.series.color;
    for (var ix = 0; ix < g.coordinates.length; ix++) {
        var xy = this.series.toCanvasCoordinates(ix);
        ctx.arc(xy.x, xy.y, 3, 0, 2 * Math.PI, true);
        ctx.fill();
    }
    ctx.restore();
};

/**
 * GraphBuilder -
 */

com.sweattrails.api.GraphBuilder = function () {
    com.sweattrails.api.Builder.call(this, "graph", com.sweattrails.api.Graph)
};

com.sweattrails.api.GraphBuilder.prototype = new com.sweattrails.api.Builder();

new com.sweattrails.api.GraphBuilder();

/**
 * http://stackoverflow.com/questions/1255512/how-to-draw-a-rounded-rectangle-on-html-canvas
 *
 * Draws a rounded rectangle using the current state of the canvas.
 * If you omit the last three params, it will draw a rectangle
 * outline with a 5 pixel border radius
 * @param {CanvasRenderingContext2D} ctx
 * @param {Number} x The top left x coordinate
 * @param {Number} y The top left y coordinate
 * @param {Number} width The width of the rectangle
 * @param {Number} height The height of the rectangle
 * @param {Number} [radius = 5] The corner radius; It can also be an object
 *                 to specify different radii for corners
 * @param {Number} [radius.tl = 0] Top left
 * @param {Number} [radius.tr = 0] Top right
 * @param {Number} [radius.br = 0] Bottom right
 * @param {Number} [radius.bl = 0] Bottom left
 * @param {Boolean} [fill = false] Whether to fill the rectangle.
 * @param {Boolean} [stroke = true] Whether to stroke the rectangle.
 */
com.sweattrails.api.roundedRect = function (x, y, width, height, radius, fill, stroke) {
    if (arguments.length < 7) {
        stroke = true;
    }
    if (arguments.length < 5) {
        radius = {tl: 5, tr: 5, br: 5, bl: 5};
    } else {
        if (typeof(radius) === 'number') {
            radius = {tl: radius, tr: radius, br: radius, bl: radius};
        } else {
            var defaultRadius = {tl: 0, tr: 0, br: 0, bl: 0};
            for (var side in defaultRadius) {
                radius[side] = radius[side] || defaultRadius[side];
            }
        }
    }
    this.beginPath();
    this.moveTo(x + radius.tl, y);
    this.lineTo(x + width - radius.tr, y);
    this.quadraticCurveTo(x + width, y, x + width, y + radius.tr);
    this.lineTo(x + width, y + height - radius.br);
    this.quadraticCurveTo(x + width, y + height, x + width - radius.br, y + height);
    this.lineTo(x + radius.bl, y + height);
    this.quadraticCurveTo(x, y + height, x, y + height - radius.bl);
    this.lineTo(x, y + radius.tl);
    this.quadraticCurveTo(x, y, x + radius.tl, y);
    this.closePath();
    if (fill) {
        this.fill();
    }
    if (stroke) {
        this.stroke();
    }
};
