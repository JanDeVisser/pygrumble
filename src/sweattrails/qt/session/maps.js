/**
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

var map; // the map object
var intervalList; // array of intervals
var markerList; // array of markers
var polyList; // array of polylines

Config = JSON.parse(bridge.getConfig());

var osm_attr = 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>';
var tile_sources = {
    OSMMapnik: {
        url: 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attributes: {
            attribution: osm_attr
        }
    },
    OpenCycleMap: {
        url: 'http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png',
        attributes: {
            attribution: '&copy; OpenCycleMap, ' + osm_attr
        }
    },
    MapQuest: {
        url: 'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
        attributes: {
            attribution: osm_attr + ' Tiles &169; <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png" />'
        }
    },
    Mapbox: {
        url:             'https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}',
        attributes: {
            attribution: 'Map data &#169; OpenStreetMap contributors, CC-BY-SA, Imagery &#169; Mapbox',
            id:          'mapbox.run-bike-hike',
            accessToken: 'pk.eyJ1IjoiamFuZGV2IiwiYSI6ImNpenBzbzFzNTAwcmgycnFnd3QycWFpbTgifQ.vIht_WItDuJwLuatY_S5xg'
        }
    }
};
var source = 'Mapbox';

function createPolyline(points, options) {
    // Populate the route path
    var path = [];
    for (var ix = 0; ix < points.length; ix++) {
        console.log("ix: " + ix + "lat: " + points[ix][0] + "lon: " + points[ix][1])
        path.push(L.latLng(points[ix][0], points[ix][1]));
    }
    return L.polyline(path, options);
}

function drawInterval(id, options) {
    var latlons = bridge.getLatLons(id);
    var line = createPolyline(latlons, options);
    line.addTo(map);
    return line;
}

function drawRoute() {
    var routeOptions = {
        color: '#FF0000',
        fill:  false
    };

    var line = drawInterval(0, routeOptions);
    line.addTo(map);
    map.fitBounds(line.getBounds());
}

function drawIntervals() {
    // intervals will be drawn with these options
    var polyOptions = {
        color: '#0000FF',
        fill:  false 
    }

    // remove previous intervals highlighted
    while (intervalList.length > 0) {
        var highlighted = intervalList.pop();
        map.removeLayer(highlighted)
    }

    // how many to draw?
    var intervals = bridge.intervalCount();
    for (var i = 1; i <= intervals; i++) {
        var line = drawInterval(i, polyOptions);
        var latlngs = line.getLatLngs();
        if (latlngs.length) {
            var end = latlngs[latlngs.length - 1];
            var marker = L.marker(end, { title: i.toString() }).addTo(map);
            markerList.push(marker);
            marker.on('click', function(event) { bridge.toggleInterval(i); });
        }
    }
}

function initialize() {
    try {
        map = L.map('map-canvas');
        var src = tile_sources[source];
        L.tileLayer(src.url, src.attributes).addTo(map);

        markerList = new Array();
        intervalList = new Array();
        polyList = new Array();

        drawRoute();
        drawIntervals();

        // bridge.drawIntervals.connect(drawIntervals)
        bridge.drawOverlays();
    } catch (e) {
        console.log("initialize(): " + e);
        throw e;
    }
}
