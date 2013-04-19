var units = [ "metric", "imperial "]
var native_unit = "{{native_unit}}"

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

// import_file('/js/st_lib.js')
