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

com.sweattrails.api.Map = function(container, id, ds) {
    this.container = container;
    this.id = id;
    this.type = "map";
    $$.register(this);
    this.mapdiv = null;
    if (arguments.length > 2) {
        this.setDataSource(arguments[2]);
    }
    this.latbridge = new com.sweattrails.api.internal.DataBridge();
    this.lonbridge = new com.sweattrails.api.internal.DataBridge();
    this.height = null;
    return this;
};

com.sweattrails.api.Map.prototype.setDataSource = function(ds) {
    this.datasource = ds;
    ds.addView(this);
};

com.sweattrails.api.Map.prototype.render = function() {
    $$.log(this, "render()");
    this.datasource.reset();
    this.datasource.execute();
};

com.sweattrails.api.Map.prototype.onData = function(data) {
    $$.log(this, "Table.onData");
    this.onrender && this.onrender(data);
    if (this.mapdiv) {
        this.container.removeChild(this.mapdiv);
    }
    this.mapdiv = document.createElement("div");
    this.mapdiv.id = this.id;
    if (this.height) {
        this.mapdiv.height = this.height;
    }
    $$.log(this, "container: " + typeof(this.container));
    this.container.appendChild(this.mapdiv);
    this.latlngs = [];
};

com.sweattrails.api.Map.prototype.noData = function() {
    $$.log(this, "Table.noData");
    var emptyrow = document.createElement("tr");
    emptyrow.id = this.id + "-emptyrow";
    this.table.appendChild(emptyrow);
    var td = document.createElement("td");
    td.style.bgcolor = "white";
    td.colSpan = this.columns.length;
    td.innerHTML = "&#160;<i>No data</i>";
    emptyrow.appendChild(td);
};

com.sweattrails.api.Map.prototype.renderData = function(obj) {
    if (!obj) return;
    $$.log(this, "Map.renderData");
    this.latlngs.push(this.getCoordinates(obj))
};

com.sweattrails.api.Map.prototype.onDataEnd = function() {
    $$.log(this, "Table.onDataEnd");
    this.map = L.map(this.id);
    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
            attribution: 'Map data copyright OpenStreetMap contributors, CC-BY-SA, Imagery copyright Mapbox',
            maxZoom: 18,
            id: 'mapbox.run-bike-hike',
            accessToken: 'pk.eyJ1IjoiamFuZGV2IiwiYSI6ImNpenBzbzFzNTAwcmgycnFnd3QycWFpbTgifQ.vIht_WItDuJwLuatY_S5xg'
        }).addTo(this.map);
    this.polyline = L.polyline(this.latlngs, {color: 'red'}).addTo(this.map);
    this.map.fitBounds(this.polyline.getBounds());
    this.onrendered && this.onrendered();
};

com.sweattrails.api.Map.prototype.setLatitudeProperty = function(prop) {
    this.latbridge.get = prop;
};

com.sweattrails.api.Map.prototype.setLongitudeProperty = function(prop) {
    this.lonbridge.get = prop;
};

com.sweattrails.api.Map.prototype.setCoordinateProperty = function(prop) {
    this.latbridge.get = prop + ".lat";
    this.lonbridge.get = prop + ".lon";
};

com.sweattrails.api.Map.prototype.getCoordinates = function(object) {
    return L.latLng(parseFloat(this.latbridge.getValue(object, this)),
        parseFloat(this.lonbridge.getValue(object, this)));
};

com.sweattrails.api.Map.prototype.reset = function(data) {
    $$.log(this, "Map.reset");
    this.datasource.reset(data);
    this.render();
};


/**
 * MapBuilder -
 */

com.sweattrails.api.MapBuilder = function() {
    this.type = "builder";
    this.name = "mapbuilder";
    $$.processor("map", this);
};

com.sweattrails.api.MapBuilder.prototype.process = function(t) {
    var p = t.parentNode;
    var name = t.getAttribute("name");
    $$.log(this, "mapBuilder: building " + name);
    var ds = com.sweattrails.api.dataSourceBuilder.build(t);
    var map = new com.sweattrails.api.Map(p, name, ds);
    if (t.getAttribute("height")) {
        map.height = t.getAttribute("height");
    }
    if (t.getAttribute("coordinate")) {
        map.setCoordinateProperty(t.getAttribute("coordinate"));
    } else {
        if (t.getAttribute("latitude")) {
            map.setLatitudeProperty(t.getAttribute("latitude"));
        }
        if (t.getAttribute("longitude")) {
            map.setLongitudeProperty(t.getAttribute("longitude"));
        }
    }
    map.onrender = t.getAttribute("onrender") && getfunc(t.getAttribute("onrender"));
    map.onrendered = t.getAttribute("onrendered") && getfunc(t.getAttribute("onrendered"));
};

new com.sweattrails.api.MapBuilder();

