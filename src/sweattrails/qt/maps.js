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
 *
 * This module uses ideas and code from GoldenCheetah:
 * Copyright (c) 2009 Greg Lonnon (greg.lonnon@gmail.com)
 *               2011 Mark Liversedge (liversedge@gmail.com)
 */

var map; // the map object
var intervalList; // array of intervals
var markerList; // array of markers
var polyList; // array of polylines

Config = JSON.parse(bridge.getConfig());

function initialize() {
	var script = document.createElement('script');
	script.type = 'text/javascript';
	script.src = 'https://maps.googleapis.com/maps/api/js?key=' + 
		Config.app.config.google_api_key + 
		'&sensor=false&callback=initMap';
	document.body.appendChild(script);
}


// Draw the entire route, we use a local js bridge object
// to supply the data to
// a) reduce bandwidth and
// b) allow local manipulation.
// This makes the UI considerably more 'snappy'
function drawRoute() {
	// route will be drawn with these options
	var routeOptionsYellow = {
		strokeColor : '#FFFF00',
		strokeOpacity : 0.4,
		strokeWeight : 10,
		zIndex : -2
	};

	// load the GPS co-ordinates
	var latlons = bridge.getLatLons(0); // interval 0 is the entire route

	// create the route Polyline
	var routeYellow = new google.maps.Polyline(routeOptionsYellow);
	routeYellow.setMap(map);

	// lastly, populate the route path
	var path = routeYellow.getPath();
	var j = 0;
	while (j < latlons.length) {
		path.push(new google.maps.LatLng(latlons[j], latlons[j + 1]));
		j += 2;
	}
}

function drawIntervals() {
	// intervals will be drawn with these options
	var polyOptions = {
		strokeColor : '#0000FF',
		strokeOpacity : 0.6,
		strokeWeight : 10,
		zIndex : -1
	// put at the bottom
	}

	// remove previous intervals highlighted
	j = intervalList.length;
	while (j) {
		var highlighted = intervalList.pop();
		highlighted.setMap(null);
		j--;
	}

	// how many to draw?
	var intervals = bridge.intervalCount();
	for (var i = 1; i <= intervals; i++) {
		var latlons = bridge.getLatLons(i);
		var intervalHighlighter = new google.maps.Polyline(polyOptions);
		intervalHighlighter.setMap(map);
		intervalList.push(intervalHighlighter);
		var path = intervalHighlighter.getPath();
		var j = 0;
		var latlng = null;
		while (j < latlons.length) {
			latlng = new google.maps.LatLng(latlons[j], latlons[j + 1])
			path.push(latlng);
			j += 2;
		}
		if (latlng) {
			var marker = new google.maps.Marker({ title: i.toString(), animation: google.maps.Animation.DROP, position: latlng });
			marker.setMap(map);
			markerList.push(marker);
			google.maps.event.addListener(marker, 'click', function(event) { bridge.toggleInterval(i); });
		}
	}
}

// initialise function called when map loaded
function initMap() {
	try {
		// TERRAIN style map please and make it draggable
		// note that because QT webkit offers touch/gesture
		// support the Google API only supports dragging
		// via gestures - this is alrady registered as a bug
		// with the google map team
		var controlOptions = {
			style : google.maps.MapTypeControlStyle.DEFAULT
		};
		var myOptions = {
			draggable : true,
			mapTypeId : google.maps.MapTypeId.TERRAIN,
			tilt : 45,
			streetViewControl : false,
		};

		// setup the map, and fit to contain the limits of the route
		map = new google.maps.Map(
			document.getElementById('map-canvas'),
			myOptions);
		box = bridge.getBoundingBox();
		var sw = new google.maps.LatLng(box[0], box[1]);
		var ne = new google.maps.LatLng(box[2], box[3]);
		var bounds = new google.maps.LatLngBounds(sw, ne);
		map.fitBounds(bounds);

		// var boundingBoxPoints = [
		// ne, new google.maps.LatLng(ne.lat(), sw.lng()),
		// sw, new google.maps.LatLng(sw.lat(), ne.lng()), ne
		// ];
		//
		// var boundingBox = new google.maps.Polyline({
		// path: boundingBoxPoints,
		// strokeColor: '#FF0000',
		// strokeOpacity: 1.0,
		// strokeWeight: 2
		// });
		// boundingBox.setMap(map);

		// add the bike layer, useful in some areas, but coverage
		// is limited, US gets best coverage at this point (Summer 2011)
		var bikeLayer = new google.maps.BicyclingLayer();
		bikeLayer.setMap(map);

		// initialise local variables
		markerList = new Array();
		intervalList = new Array();
		polyList = new Array();

		// draw the main route data, getting the geo
		// data from the JS bridge - reduces data sent/received
		// to the map server and makes the UI pretty snappy
		drawRoute();
		drawIntervals();

		// catch signals to redraw intervals
		// bridge.drawIntervals.connect(drawIntervals)
		bridge.drawOverlays();
	} catch (e) {
		console.log("initialize(): " + e);
		throw e;
	}
}
