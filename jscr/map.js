/*
 * Copyright (c) 2017 Jan de Visser (jan@sweattrails.com)
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

com.sweattrails.api.internal.MapLayer = function(parent, id) {
    if (parent) {
        this.parent = parent;
        this.map = parent;
        while (this.map.parent) {
            this.map = this.map.parent;
        }
        this.id = id;
    }
};

com.sweattrails.api.internal.MapLayer.prototype.make = function() {
    return null;
};

com.sweattrails.api.internal.MapLayer.prototype.render = function(fnc) {
    var ret = this.make();
    if (ret) {
        this.layer = ret;
        fnc && fnc(this);
    } else {
        this.reserve(fnc)
    }
    return ret;
};

com.sweattrails.api.internal.MapLayer.prototype.getBounds = function() {
    return this.layer && this.layer.getBounds && this.layer.getBounds();
};

com.sweattrails.api.internal.MapLayer.prototype.getLabel = function() {
    return this.label;
};

com.sweattrails.api.internal.MapLayer.prototype.isBaseLayer = function() {
    return false;
};

com.sweattrails.api.internal.MapLayer.prototype.reserve = function(fnc) {
    this.ticket = this.map.reserve(fnc);
};

com.sweattrails.api.internal.MapLayer.prototype.redeem = function() {
    this.map.redeem(this);
};

com.sweattrails.api.internal.MapLayer.prototype.drop = function(ev1, ev2) {
    if (this.draw) {
        this.draw(ev1, ev2);
    } else {
        this.ondrop && this.ondrop(ev1, ev2);
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.TileLayers = {
    "mapbox": {
        "streets": {
            url: "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}",
            label: "Mapbox Streets",
            theme: "light",
            attribution: 'Map data &#169; OpenStreetMap contributors, CC-BY-SA, Imagery &#169; Mapbox',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken: 'pk.eyJ1IjoiamFuZGV2IiwiYSI6ImNpenBzbzFzNTAwcmgycnFnd3QycWFpbTgifQ.vIht_WItDuJwLuatY_S5xg'
        },
        "bikehike": {
            url: "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}",
            label: "Mapbox Bike-Hike",
            theme: "light",
            attribution: 'Map data &#169; OpenStreetMap contributors, CC-BY-SA, Imagery &#169; Mapbox',
            maxZoom: 18,
            id: 'mapbox.run-bike-hike',
            accessToken: 'pk.eyJ1IjoiamFuZGV2IiwiYSI6ImNpenBzbzFzNTAwcmgycnFnd3QycWFpbTgifQ.vIht_WItDuJwLuatY_S5xg'
        },
        "dark": {
            url: 'https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}',
            label: "Mapbox Dark",
            theme: "dark",
            attribution: 'Map data &#169; OpenStreetMap contributors, CC-BY-SA, Imagery &#169; Mapbox',
            id: 'mapbox.dark',
            accessToken: 'pk.eyJ1IjoiamFuZGV2IiwiYSI6ImNpenBzbzFzNTAwcmgycnFnd3QycWFpbTgifQ.vIht_WItDuJwLuatY_S5xg'
        }
    },
    "osm": {
        "basic": {
            url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            label: "OpenStreetMap",
            theme: "light",
            attribution: 'Map data &#169; OpenStreetMap contributors'
        },
        "opencyclemap": {
            url: "http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png",
            label: "OpenCycleMap",
            theme: "light",
            attribution: 'Map data &#169; OpenStreetMap contributors'
        }
    }
};

com.sweattrails.api.TileLayer = function(parent, id, url, descr) {
    if (arguments.length == 2) {
        var l = __.getvar(id, com.sweattrails.api.TileLayers);
        if (l) {
            this.label = l["label"];
            this.url = l["url"];
            this.descr = l;
        }
    } else {
        this.label = descr.label || id;
        this.url = url;
        this.descr = descr;
    }
    com.sweattrails.api.internal.MapLayer.call(this, parent, id);
};

com.sweattrails.api.TileLayer.prototype = new com.sweattrails.api.internal.MapLayer();

com.sweattrails.api.TileLayer.prototype.make = function() {
    return new L.tileLayer(this.url, this.descr);
}

com.sweattrails.api.TileLayer.prototype.isBaseLayer = function() {
    return true;
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.DataLayer = function(parent, id, ds, label, options) {
    this.label = label;
    this.ds = ds;
    ds && ds.addView(this);
    this.options = options;
    this.latbridge = new com.sweattrails.api.internal.DataBridge();
    this.lonbridge = new com.sweattrails.api.internal.DataBridge();
    this.altbridge = new com.sweattrails.api.internal.DataBridge();
    this.widthbridge = new com.sweattrails.api.internal.DataBridge();
    this.heightbridge = new com.sweattrails.api.internal.DataBridge();
    com.sweattrails.api.internal.MapLayer.call(this, parent, id);
};

com.sweattrails.api.internal.DataLayer.prototype = new com.sweattrails.api.internal.MapLayer();

com.sweattrails.api.internal.DataLayer.prototype.make = function(fnc) {
    this.ds.reset();
    this.ds.execute();
    return null;
};

com.sweattrails.api.internal.DataLayer.prototype.setLatitudeProperty = function(prop) {
    this.latbridge.get = prop;
};

com.sweattrails.api.internal.DataLayer.prototype.setLongitudeProperty = function(prop) {
    this.lonbridge.get = prop;
};

com.sweattrails.api.internal.DataLayer.prototype.setCoordinateProperty = function(prop) {
    this.latbridge.get = prop + ".lat";
    this.lonbridge.get = prop + ".lon";
};

com.sweattrails.api.internal.DataLayer.prototype.setAltitudeProperty = function(prop) {
    this.altbridge.get = prop;
};

com.sweattrails.api.internal.DataLayer.prototype.setWidthProperty = function(prop) {
    this.widthbridge.get = prop;
};

com.sweattrails.api.internal.DataLayer.prototype.setHeightProperty = function(prop) {
    this.heightbridge.get = prop;
};

com.sweattrails.api.internal.DataLayer.prototype.setSizeProperty = function(prop) {
    this.widthbridge.get = prop + ".width";
    this.heightbridge.get = prop + ".height";
};

com.sweattrails.api.internal.DataLayer.prototype.getCoordinates = function(object) {
    var lat = parseFloat(this.latbridge.getValue(object, this));
    var lon = parseFloat(this.lonbridge.getValue(object, this));
    var ret = (!isNaN(lat) && !isNaN(lon)) ? L.latLng(lat, lon) : null;
    var alt = parseFloat(this.altbridge.getValue(object, this));
    if (!isNaN(alt)) {
        ret.alt = alt;
    }
    var width = parseFloat(this.widthbridge.getValue(object, this));
    var height = parseFloat(this.heightbridge.getValue(object, this));
    if (!isNaN(width) && !isNaN(height)) {
        ret.size = L.point(width, height);
    }
    return ret;
};

com.sweattrails.api.internal.DataLayer.prototype.onData = function(data) {
    $$.log(this, "onData");
    this.latlngs = [];
    this.invalid = 0;
};

com.sweattrails.api.internal.DataLayer.prototype.noData = function() {
    $$.log(this, "noData");
    this.redeem();
};

com.sweattrails.api.internal.DataLayer.prototype.renderData = function(obj) {
    if (!obj) return;
    var coords = this.getCoordinates(obj);
    if (coords) {
        this.latlngs.push(coords);
    } else {
        this.invalid += 1;
    }
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.TrailLayer = function(parent, ds, id, label, options) {
    com.sweattrails.api.internal.DataLayer.call(this, parent, id, ds, label, options);
};

com.sweattrails.api.TrailLayer.prototype = new com.sweattrails.api.internal.DataLayer();

com.sweattrails.api.TrailLayer.prototype.onDataEnd = function() {
    $$.log(this, "Map.onDataEnd. %d valid coordinates, %d invalid", this.latlngs.length, this.invalid);
    this.layer = new L.polyline(this.latlngs, this.options);
    this.redeem();
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.IconLayer = function(parent, id, ds, label, options) {
    this.icons = [];
    this.size = (options.width && options.height)
        ? new L.point(options.width, options.height)
        : new L.point(32, 32);
    this.size_y = options.size_y || 32;
    com.sweattrails.api.internal.DataLayer.call(this, parent, id, ds, label, options);
};

com.sweattrails.api.IconLayer.prototype = new com.sweattrails.api.internal.DataLayer();

com.sweattrails.api.internal.DataLayer.prototype.noData = function() {
    $$.log(this, "noData");
    this.layer = new L.layerGroup();
    this.redeem();
};

com.sweattrails.api.IconLayer.prototype.onDataEnd = function() {
    this.layer = new L.layerGroup();
    var _ = this;
    this.latlngs.forEach(function(latlng) {
        var sz = latlng.size ? latlng.size : this.size;
        _.icons.push(_.dropIcon(latlng, sz));
    });
    this.redeem();
};

com.sweattrails.api.IconLayer.prototype.dropIcon = function(latlng, size) {
    return new L.marker(latlng, {
        icon: new L.icon( {
            iconUrl: this.options.icon,
            iconSize: size,
            iconAnchor: [0, 0]
        }),
        draggable: true
    }).addTo(this.layer);
};

com.sweattrails.api.IconLayer.prototype.ondrop = function(ev1, ev2) {
    var sz;
    if (!ev2 || this.size.contains(ev2.layerPoint.subtract(ev1.layerPoint))) {
        sz = this.size;
    } else {
        sz = ev2.layerPoint.subtract(ev1.layerPoint);
    }
    this.icons.push(this.dropIcon(ev1.latlng, sz));
};


/* ----------------------------------------------------------------------- */

com.sweattrails.api.GPXLayer = function(parent, options) {
    this.url = options.url;
    this.options = options;
    this.options.async = true;
    com.sweattrails.api.internal.MapLayer.call(this, parent, options.id || options.name);
};

com.sweattrails.api.GPXLayer.prototype = new com.sweattrails.api.internal.MapLayer();

com.sweattrails.api.GPXLayer.prototype.make = function() {
    var _ = this;
    this.layer = new L.GPX(this.url, this.options).on('loaded', function(e) {
        _.redeem();
    });
    return null;
}

com.sweattrails.api.GPXLayer.prototype.getLabel = function() {
    return (this.layer) ? this.layer.get_name() : this.options.label;
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.CustomLayer = function(parent, options) {
    if (values) {
        for (n in values) {
            this[n] = values[n];
        }
    }
    this.makefnc = (typeof(this.makefnc) === "function") ? this.makefnc : __.getvar(this.makefnc);
    this.initialize = this.initialize && ((typeof(this.initialize) === "function") ? this.initialize : __.getvar(this.initialize));
    com.sweattrails.api.internal.MapLayer.call(this, parent, id);
    this.initialize && this.initialize();
}

com.sweattrails.api.CustomLayer.prototype = new com.sweattrails.api.internal.MapLayer();

com.sweattrails.api.CustomLayer.prototype.make = function() {
    return this.makefnc()
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.LayerControl = function(parent, layers, options) {
    this.descr = "Layer Control";
    this.layers = [];
    var _this = this;
    layers && layers.forEach(function(l) { _this.addLayer(l); });
    this.options = options;
    this.first = null;0
    com.sweattrails.api.internal.MapLayer.call(this, parent, "layercontrol");
};

com.sweattrails.api.LayerControl.prototype = new com.sweattrails.api.internal.MapLayer();

com.sweattrails.api.LayerControl.prototype.make = function(fnc) {
    this.layer = new L.control.layers(null, null, this.options);
    var _ = this;
    this.layers.forEach(function(l) {
        l.render(function(l) {
            if (l.isBaseLayer()) {
                if (!_.first) {
                    l.layer.addTo(l.map.map);
                    _.first = l;
                }
                _.layer.addBaseLayer(l.layer, l.getLabel());
            } else {
                l.layer.addTo(l.map.map);
                _.layer.addOverlay(l.layer, l.getLabel());
            }
        });
    });
    return this.layer;
};

com.sweattrails.api.LayerControl.prototype.addLayer = function(layer) {
    this.layers.push(layer);
};

com.sweattrails.api.LayerControl.prototype.getLayer = function(id) {
    return this.layers.reduce(function(found, l) {
        if (!found) {
            if (l.getLayer) {
                found = l.getLayer(id);
            } else if (l.id === id) {
                found = l;
            }
        }
        return found;
    }, null);
};

com.sweattrails.api.LayerControl.prototype.getBounds = function() {
    var bounds = null;
    this.layers.forEach(function(layer) {
        var b = layer.getBounds();
        if (b) {
            if (!bounds) {
                bounds = b;
            } else {
                bounds.extend(b);
            }
        }
    });
    return bounds;
};

/* ----------------------------------------------------------------------- */

com.sweattrails.api.Map = function(container, options) {
    this.container = container;
    this.parent = null;
    this.options = options;
    this.id = options.id || options.name;
    this.type = "map";
    $$.register(this);
    this.layers = [];
    this.mapdiv = null;
    this.map = null;
    this.height = (options.height) ? options.height : null;
    this.onrender = options.onrender && __.getfunc(options.onrender);
    this.onrendered = options.onrendered && __.getfunc(options.onrendered);
    this.onclick = options.onclick && __.getfunc(options.onclick);
    this.onresize = options.onresize && __.getfunc(options.onresize);
    this.selectedLayer = options.selectedLayer && __.getfunc(options.selectedLayer);
    this.initialize = options.initialize && __.getfunc(options.initialize);
    this.initialize && this.initialize(options);
};

com.sweattrails.api.Map.prototype.setDataSource = function(ds) {
    this.datasource = ds;
};

com.sweattrails.api.Map.prototype.render = function() {
    $$.log(this, "render()");
    this.onrender && this.onrender(data);
    if (!this.mapdiv) {
        this.mapdiv = document.createElement("div");
        this.mapdiv.id = "map-" + this.id;
        if (this.height) {
            this.mapdiv.height = this.height;
        }
        this.container.appendChild(this.mapdiv);
        this.map = L.map(this.mapdiv, { preferCanvas: true, doubleClickZoom: false });
        if (this.onclick) {
            this.map.on("click", this.onclick, this);
        } else {
            this.map.on("click", this.click, this)
        }
        if (this.onresize) {
            this.map.on("resize", this.onresize, this);
        }
        this.tickets = [];
        _ = this;
        this.layers.forEach(function(layer) {
            layer.render(function(layer) {
                layer.layer.addTo(_.map);
            });
        });
        this.countReservations();
        $$.log(this, "Map object created");
    }
};

com.sweattrails.api.Map.prototype.click = function(ev) {
    if (!this._click) {
        this._click = ev;
    } else {
        this.drop(this._click, ev);
        this._click = null;
    }
};

com.sweattrails.api.Map.prototype.drop = function(ev1, ev2) {
    var layer = this.selectedLayer && this.selectedLayer()
    if (layer) {
        // var inputs = document.getElementById("iconChoices.getElementsByTagName("input;
        // for (var ix = 0; ix < inputs.length; ix++ ) {
        //     var input = inputs.item(ix);
        //     if (input.checked) {
        //         layer = this._iconlayers[input.value];
        //     }
        // }
        layer.drop(ev1, ev2);
    }
};

com.sweattrails.api.Map.prototype.addLayer = function(layer) {
    this.layers.push(layer);
};

com.sweattrails.api.Map.prototype.getLayer = function(id) {
    return this.layers.reduce(function(found, l) {
        if (!found) {
            if (l.getLayer) {
                found = l.getLayer(id);
            } else if (l.id === id) {
                found = l;
            }
        }
        return found;
    }, null);
};

com.sweattrails.api.Map.prototype.reserve = function(fnc) {
    return this.tickets.push(fnc ? fnc : true) - 1;
};

com.sweattrails.api.Map.prototype.redeem = function(layer) {
    if (layer.ticket >= 0) {
        layer.layer.addTo(this.map);
        fnc = this.tickets[layer.ticket];
        (typeof(fnc) === "function") && fnc(layer);
        this.tickets[layer.ticket] = false;
        this.countReservations()
        layer.ticket = -1;
    }
};

com.sweattrails.api.Map.prototype.countReservations = function() {
    if (this.tickets) {
        var sum = 0;
        this.tickets.forEach(function(x) { sum += (x ? 1 : 0) });
        if (!sum) {
            this.tickets = null;
            $$.async(this);
        }
    }
};

com.sweattrails.api.Map.prototype.onASync = function() {
    if (this.map) {
        var bounds = null;
        this.layers.forEach(function(layer) {
            var b = layer.getBounds();
            if (b) {
                if (!bounds) {
                    bounds = b;
                } else {
                    bounds.extend(b);
                }
            }
        });
        if (bounds) {
            this.map.invalidateSize();
            this.map.fitBounds(bounds);
        }
        this.onrendered && this.onrendered();
    }
};

com.sweattrails.api.Map.prototype.renderImage = function(container) {
    var _ = this;
    var img = document.createElement('img');
    var dimensions = this.map.getSize();
    img.width = dimensions.x / 2;
    img.height = dimensions.y / 2;
    img.src = "/image/throbber.gif";
    container.appendChild(img);
    leafletImage(this.map, function(err, canvas) {
        img.src = canvas.toDataURL();
    });
    return img;
};

com.sweattrails.api.Map.prototype.download = function(name) {
    var img = this.renderImage(document.body);
    var link = document.createElement("a");
    link.download = (name) ? name : "prettymap.png";
    link.href = img.src;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    delete link;
    document.body.removeChild(img);
    delete img;
};


/**
 * MapBuilder -
 */

com.sweattrails.api.MapBuilder = function() {
    this.type = "builder";
    this.name = "mapbuilder";
    this.builders = {
        "trail": this.buildTrail,
        "icons": this.buildIcons,
        "gpx": this.buildGPX,
        "tile": this.buildTile,
        "layers": this.buildLayers,
        "custom": this.buildCustom
    };
    $$.processor("map", this);
};

com.sweattrails.api.MapBuilder.prototype.parseOptions = function(elem, suboptions, level) {
    if (typeof(level) === "undefined") {
        level = 0;
    }
    var ret = {};
    var children = elem.childNodes;
    for (var ix = 0; ix < children.length; ix++) {
        var c = children[ix];
        var n = c.localName;
        if ((n === "option") || (n === "value")) {
            ret[c.getAttribute("name")] = c.textContent;
        } else if (suboptions && (typeof(suboptions[n]) !== "undefined")) {
            ret[n] = this.parseOptions(c, suboptions[n], level+1);
        }
    }
    if (level == 0) {
        for (let attr of elem.getAttributeNames()) {
            ret[attr] = elem.getAttribute(attr);
        }
    }
    return ret;
}

com.sweattrails.api.MapBuilder.prototype.buildGPX = function(parent, elem, attachTo) {
    var options = this.parseOptions(elem, {
        polyline_options: null,
        marker_options: { wptIconUrls: null }
    });
    parent.addLayer(new com.sweattrails.api.GPXLayer(parent, options));
};

com.sweattrails.api.MapBuilder.prototype.buildTile = function(parent, elem, attachTo) {
    var l = null;
    var id = elem.getAttribute("id");
    if (id) {
        if (!__.getvar(id, com.sweattrails.api.TileLayers)) {
            $$.log(this, "Tile Layer with id %s not found", id);
        } else {
            l = new com.sweattrails.api.TileLayer(parent, id);
        }
    } else {
        var label = elem.getAttribute("label");
        var url = elem.getAttribute("url");
        var descr = this.parseOptions(elem, null);
        l = new com.sweattrails.api.TileLayer(parent, id, label, url, descr);
    }
    l && parent.addLayer(l);
};

com.sweattrails.api.MapBuilder.prototype.buildTrail = function(parent, elem, attachTo) {
    return this.buildDataLayer(parent, elem, attachTo, com.sweattrails.api.TrailLayer);
};

com.sweattrails.api.MapBuilder.prototype.buildIcons = function(parent, elem, attachTo) {
    return this.buildDataLayer(parent, elem, attachTo, com.sweattrails.api.IconLayer);
};

com.sweattrails.api.MapBuilder.prototype.buildDataLayer = function(parent, elem, attachTo, factory) {
    var ds = com.sweattrails.api.dataSourceBuilder.build(elem);
    var options = this.parseOptions(elem);
    var layer = new factory(parent, options.id, ds, options.label, options);
    if (options.coordinate) {
        layer.setCoordinateProperty(options.coordinate);
    } else {
        if (options.latitude) {
            layer.setLatitudeProperty(options.latitude);
        }
        if (options.longitude) {
            layer.setLongitudeProperty(options.longitude);
        }
    }
    if (options.altitude) {
        layer.setAltitudeProperty(options.altitude);
    }
    if (options.size) {
        layer.setSizeProperty(options.size);
    } else {
        if (options.width) {
            layer.setWidthProperty(options.width);
        }
        if (options.height) {
            layer.setHeightProperty(options.height);
        }
    }
    parent.addLayer(layer);
};

com.sweattrails.api.MapBuilder.prototype.buildLayers = function(parent, elem, attachTo) {
    var layer = new com.sweattrails.api.LayerControl(parent, null, this.parseOptions(elem));
    parent.addLayer(layer);
    this.copyNode(layer, elem, attachTo);
};

com.sweattrails.api.MapBuilder.prototype.buildCustom = function(parent, elem, attachTo) {
    var options = this.parseOptions(elem);
    var layer = new com.sweattrails.api.CustomLayer(parent, options);
    parent.addLayer(layer);
    this.copyNode(layer, elem, attachTo);
};

com.sweattrails.api.MapBuilder.prototype.process = function(t) {
    var p = t.parentElement;
    var options = this.parseOptions(t);
    $$.log(this, "mapBuilder: building " + options.id || options.name);
    var map = new com.sweattrails.api.Map(p, options);
    this.copyNode(map, t, p);
};

com.sweattrails.api.MapBuilder.prototype.copyNode = function (parent, elem, attachTo) {
    var children = elem.childNodes;
    for (var ix = 0; ix < children.length; ix++) {
        var c = children[ix];
        if (c.namespaceURI === com.sweattrails.api.xmlns) {
            var n = c.localName;
            this.builders[n] && this.builders[n].bind(this)(parent, c, attachTo);
        } else {
            var childClone = c.cloneNode(false);
            attachTo.appendChild(childClone);
            this.copyNode(parent, c, childClone);
        }
    }
};

new com.sweattrails.api.MapBuilder();
