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

com.sweattrails.api.internal.MapLayer = class {
    constructor(parent, id) {
        if (parent) {
            this.parent = parent;
            this.map = parent;
            while (this.map.parent) {
                this.map = this.map.parent;
            }
        }
        this.id = id;
    }

    make() {
        return null;
    }

    render(fnc) {
        var ret = this.make();
        if (ret) {
            this.layer = ret;
            fnc && fnc(this);
        } else {
            this.reserve(fnc)
        }
        return ret;
    }

    getBounds() {
        return this.layer && this.layer.getBounds && this.layer.getBounds();
    }

    getLabel() {
        return this.label;
    }

    isBaseLayer() {
        return false;
    }

    reserve(fnc) {
        this.ticket = this.map.reserve(fnc);
    }

    redeem() {
        this.map.redeem(this);
    }

    drop(ev1, ev2) {
        if (this.draw) {
            this.draw(ev1, ev2);
        } else {
            this.ondrop && this.ondrop(ev1, ev2);
        }
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
            url: "https://{s}.tile.thunderforest.com/cycle/{z}/{x}/{y}.png?apikey=684e46dff08a4c6cbd8641ae6b1c1df2",
            label: "OpenCycleMap",
            theme: "light",
            attribution: 'Maps &#169; Thunderforest, data &#169; OpenStreetMap contributors'
        }
    },
    "thunderforest": {
        "landscape": {
            url: "https://{s}.tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey=684e46dff08a4c6cbd8641ae6b1c1df2",
            label: "Thunderforest Landscape",
            theme: "light",
            attribution: 'Maps &#169; Thunderforest, data &#169; OpenStreetMap contributors'
        },
        "outdoors": {
            url: "https://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=684e46dff08a4c6cbd8641ae6b1c1df2",
            label: "Thunderforest Outdoors",
            theme: "light",
            attribution: 'Maps &#169; Thunderforest, data &#169; OpenStreetMap contributors'
        },
        "transport": {
            url: "https://{s}.tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey=684e46dff08a4c6cbd8641ae6b1c1df2",
            label: "Thunderforest Transport",
            theme: "light",
            attribution: 'Maps &#169; Thunderforest, data &#169; OpenStreetMap contributors'
        }
    }
};

com.sweattrails.api.TileLayer = class extends com.sweattrails.api.internal.MapLayer {
    constructor(parent, id, url, descr) {
        super(parent, id);
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
    }

    make() {
        return new L.tileLayer(this.url, this.descr);
    }

    isBaseLayer() {
        return true;
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.DataLayer = class extends com.sweattrails.api.internal.MapLayer {
    constructor(parent, id, ds, label, options) {
        super(parent, id);
        this.label = label;
        this.ds = ds;
        ds && ds.addView(this);
        this.options = options;
        this.latbridge = new com.sweattrails.api.internal.DataBridge();
        this.lonbridge = new com.sweattrails.api.internal.DataBridge();
        this.altbridge = new com.sweattrails.api.internal.DataBridge();
        this.widthbridge = new com.sweattrails.api.internal.DataBridge();
        this.heightbridge = new com.sweattrails.api.internal.DataBridge();
    };

    make(fnc) {
        this.ds.reset();
        this.ds.execute();
        return null;
    }

    setLatitudeProperty(prop) {
        this.latbridge.get = prop;
    }

    setLongitudeProperty(prop) {
        this.lonbridge.get = prop;
    }

    setCoordinateProperty(prop) {
        this.latbridge.get = prop + ".lat";
        this.lonbridge.get = prop + ".lon";
    }

    setAltitudeProperty(prop) {
        this.altbridge.get = prop;
    }

    setWidthProperty(prop) {
        this.widthbridge.get = prop;
    }

    setHeightProperty(prop) {
        this.heightbridge.get = prop;
    }

    setSizeProperty(prop) {
        this.widthbridge.get = prop + ".width";
        this.heightbridge.get = prop + ".height";
    }

    getCoordinates(object) {
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
    }

    onData(data) {
        $$.log(this, "onData");
        this.latlngs = [];
        this.invalid = 0;
    }

    noData() {
        $$.log(this, "noData");
        this.redeem();
    }

    renderData(obj) {
        if (!obj) return;
        var coords = this.getCoordinates(obj);
        if (coords) {
            this.latlngs.push(coords);
        } else {
            this.invalid += 1;
        }
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.TrailLayer = class extends com.sweattrails.api.internal.DataLayer {
    constructor(parent, id, ds, label, options) {
        super(parent, id, ds, label, options);
    }

    onDataEnd() {
        $$.log(this, "Map.onDataEnd. %d valid coordinates, %d invalid", this.latlngs.length, this.invalid);
        this.layer = new L.polyline(this.latlngs, this.options);
        this.redeem();
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.IconLayer = class extends com.sweattrails.api.internal.DataLayer {
    constructor(parent, id, ds, label, options) {
        super(parent, id, ds, label, options);
        this.icons = [];
        this.size = (options.fallback.width && options.fallback.height)
            ? new L.point(options.fallback.width, options.fallback.height)
            : new L.point(32, 32);
    }

    noData() {
        $$.log(this, "noData");
        this.layer = new L.layerGroup();
        this.redeem();
    }

    onDataEnd() {
        this.layer = new L.layerGroup();
        var _ = this;
        this.latlngs.forEach(function(latlng) {
            var sz = latlng.size ? latlng.size : this.size;
            _.icons.push(_.dropIcon(latlng, sz));
        });
        this.redeem();
    }

    dropIcon(latlng, size) {
        return new L.marker(latlng, {
            icon: new L.icon( {
                iconUrl: this.options.icon,
                iconSize: size,
                iconAnchor: [0, 0]
            }),
            draggable: true
        }).addTo(this.layer);
    }

    ondrop(ev1, ev2) {
        var sz;
        if (!ev2 || this.size.contains(ev2.layerPoint.subtract(ev1.layerPoint))) {
            sz = this.size;
        } else {
            sz = ev2.layerPoint.subtract(ev1.layerPoint);
        }
        this.icons.push(this.dropIcon(ev1.latlng, sz));
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.GPXLayer = class extends com.sweattrails.api.internal.MapLayer {
    constructor(parent, options) {
        super(parent, options.id || options.name);
        this.url = options.url;
        this.options = options;
        this.options.async = true;
    }

    make() {
        var _ = this;
        this.layer = new L.GPX(this.url, this.options).on('loaded', function(e) {
            _.redeem();
        });
        return null;
    }

    getLabel() {
        return (this.layer) ? this.layer.get_name() : this.options.label;
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.CustomLayer = class extends com.sweattrails.api.internal.MapLayer {
    constructor(parent, options) {
        super(parent, options.id || options.name);
        for (n in options) {
            this[n] = options[n];
        }
        this.makefnc = (typeof(this.makefnc) === "function") ? this.makefnc : __.getfunc(this.makefnc);
        this.initialize = this.initialize && ((typeof(this.initialize) === "function") ? this.initialize : __.getfunc(this.initialize));
        this.initialize && this.initialize();
    }

    make() {
        return this.makefnc()
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.internal.Layered = {
    addLayer(layer) {
        this.layers.push(layer);
    },

    getLayer(id) {
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
    },

    getBounds() {
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
    }
}

/* ----------------------------------------------------------------------- */

com.sweattrails.api.LayerControl = class extends com.sweattrails.api.internal.MapLayer {
    constructor(parent, layers, options) {
        super(parent, "layercontrol");
        this.descr = "Layer Control";
        this.layers = [];
        var _this = this;
        layers && layers.forEach(function(l) { _this.addLayer(l); });
        this.options = options;
        this.first = null;0
    }

    make(fnc) {
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
    }

    addLayer(layer) {
        this.layers.push(layer);
    }

    getLayer(id) {
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
    }

    getBounds() {
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
    }
}

__.mixin(com.sweattrails.api.LayerControl, com.sweattrails.api.internal.Layered);

/* ----------------------------------------------------------------------- */

com.sweattrails.api.Map = class {
    constructor(container, options) {
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

    setDataSource(ds) {
        this.datasource = ds;
    };

    render() {
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
                this.map.o = functionn("resize", this.onresize, this);
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
    }

    click(ev) {
        if (!this._click) {
            this._click = ev;
        } else {
            this.drop(this._click, ev);
            this._click = null;
        }
    }

    drop(ev1, ev2) {
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
    }

    reserve(fnc) {
        return this.tickets.push(fnc ? fnc : true) - 1;
    }

    redeem(layer) {
        if (layer.ticket >= 0) {
            layer.layer.addTo(this.map);
            let fnc = this.tickets[layer.ticket];
            (typeof(fnc) === "function") && fnc(layer);
            this.tickets[layer.ticket] = false;
            this.countReservations()
            layer.ticket = -1;
        }
    }

    countReservations() {
        if (this.tickets) {
            var sum = 0;
            this.tickets.forEach(function(x) { sum += (x ? 1 : 0) });
            if (!sum) {
                this.tickets = null;
                $$.async(this);
            }
        }
    }

    onASync() {
        if (this.map) {
            let bounds = this.getBounds();
            if (bounds) {
                this.map.invalidateSize();
                this.map.fitBounds(bounds);
            }
            this.onrendered && this.onrendered();
        }
    }

    renderImage(container) {
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
    }

    download(name) {
        let img = this.renderImage(document.body);
        let link = document.createElement("a");
        link.download = (name) ? name : "map.png";
        link.href = img.src;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        document.body.removeChild(img);
    }
}

__.mixin(com.sweattrails.api.Map, com.sweattrails.api.internal.Layered);

/**
 * MapBuilder -
 */

com.sweattrails.api.MapBuilder = class  {
    constructor() {
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
    }

    parseOptions(elem, suboptions, level) {
        if (typeof(level) === "undefined") {
            level = 0;
        }
        var ret = {};
        var children = elem.childNodes;
        for (var ix = 0; ix < children.length; ix++) {
            var c = children[ix];
            var n = c.localName;
            if (((n === "option") || (n === "value")) && c.getAttribute("name")) {
                ret[c.getAttribute("name")] = c.getAttribute("value") || c.textContent;
            } else if (suboptions && (typeof(suboptions[n]) !== "undefined")) {
                ret[n] = this.parseOptions(c, suboptions[n], level+1);
            }
        }
        if (level == 0) {
            for (let attr of elem.getAttributeNames()) {
                ret[attr] = elem.getAttribute(attr);
            }
        }
        // Convert "[xxx, yyy]" to an array.
        for (let attr in ret) {
            var t = ret[attr];
            if (/^\[\ *(-?\d+\ *(,\ *-?\d+\ *)*)*\ *\]$/.test(t)) {
               ret[attr] = eval(t);
            }
        }
        return ret;
    }

    buildGPX(parent, elem, attachTo) {
        var options = this.parseOptions(elem, {
            polyline_options: null,
            marker_options: { wptIconUrls: null }
        });
        parent.addLayer(new com.sweattrails.api.GPXLayer(parent, options));
    }

    buildTile(parent, elem, attachTo) {
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
    }

    buildTrail(parent, elem, attachTo) {
        return this.buildDataLayer(parent, elem, attachTo, com.sweattrails.api.TrailLayer);
    }

    buildIcons(parent, elem, attachTo) {
        return this.buildDataLayer(parent, elem, attachTo, com.sweattrails.api.IconLayer);
    }

    buildDataLayer(parent, elem, attachTo, factory) {
        var ds = com.sweattrails.api.dataSourceBuilder.build(elem);
        var options = this.parseOptions(elem, { fallback: {} });
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
    }

    buildLayers(parent, elem, attachTo) {
        var layer = new com.sweattrails.api.LayerControl(parent, null, this.parseOptions(elem));
        parent.addLayer(layer);
        this.copyNode(layer, elem, attachTo);
    }

    buildCustom(parent, elem, attachTo) {
        var options = this.parseOptions(elem);
        var layer = new com.sweattrails.api.CustomLayer(parent, options);
        parent.addLayer(layer);
        this.copyNode(layer, elem, attachTo);
    }

    process(t) {
        var p = t.parentElement;
        var options = this.parseOptions(t);
        $$.log(this, "mapBuilder: building " + options.id || options.name);
        var map = new com.sweattrails.api.Map(p, options);
        this.copyNode(map, t, p);
    }

    copyNode (parent, elem, attachTo) {
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
    }
}

new com.sweattrails.api.MapBuilder();
