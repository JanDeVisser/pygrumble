function obj_to_latlng(obj) {
    console.log("------> obj_to_latlng: " + obj + " <" + typeof(obj) + ">");
    return new google.maps.LatLng(obj.lat, obj.lon);
}

function latlng_to_obj(latlng) {
    var ret = {
        "lat": latlng.lat(),
        "lon": latlng.lon()
    }
    return ret;
}


function execute_job(job) {
    if (typeof(job) === "function") {
        job();
    } else if (typeof(job) === "string") {
        var f = getfunc(job);
        f();
    } else if (typeof(job) === "object") {
        job.run && job.run();
    }
}

com.sweattrails.api.internal.queues = {};

com.sweattrails.api.internal.Queue = function(name) {
    this.jobs = [];
    com.sweattrails.api.internal.queues[name] = this;
    this.done = false;
    return this;
};

com.sweattrails.api.internal.Queue.prototype.add = function(job) {
    this.jobs.push(job);
};

com.sweattrails.api.internal.Queue.prototype.flush = function() {
    for (var ix = 0; ix < this.jobs.length; ix++) {
        execute_job(this.jobs[ix]);
    }
    this.jobs = [];
    this.done = true;
};

function add_to_queue(name, job) {
    var q = com.sweattrails.api.internal.queues[name];
    if (!q) {
        q = new com.sweattrails.api.internal.Queue(name);
    }
    q.add(job);
}

function flush_queue(name) {
    var q = com.sweattrails.api.internal.queues[name];
    q && q.flush();
}

function loadGMapsCallback() {
    console.log("Gmaps loaded");
    flush_queue("gmaps");
}

function loadGMaps(job) {
    if ((typeof(google) === "undefined") || !google.maps) {
        add_to_queue("gmaps", job);
        var script = document.createElement("script");
        script.type = "text/javascript";
        script.src = "http://maps.googleapis.com/maps/api/js?key=" + google_api_key + "&sensor=false&callback=loadGMapsCallback";
        console.log("About to load gmaps");
        document.body.appendChild(script);
    } else {
        execute_job(job);
    }
}

com.sweattrails.api.GeocodeField = function(fld, elem) {
    this.field = fld;
};

com.sweattrails.api.GeocodeField.prototype.renderEdit = function(value) {
    this.div 
    this.control = document.createElement("input");
    this.control.value = value || "";
    this.control.name = this.field.id;
    this.control.id = this.field.id;
    this.control.type = "text";
    if (this.size) this.control.size = this.size;
    if (this.maxlength) this.control.maxLength = this.maxlength;
    this.control.onchange = this.field.onValueChange.bind(this.field);
    var ret = document.createElement("div");
    ret.id = "mapview-" + this.field.id;
    return this.control;
};

com.sweattrails.api.GeocodeField.prototype.setValueFromControl = function(bridge, object) {
    var address = this.control.value;
    var geocoder = new google.maps.Geocode();
    this.latlng = null;
    this.status = null;
    console.log("Geocoding '" + address + "'");
    var field = this;
    geocoder.geocode( { 'address': address}, function(results, status) {
        field.status = status;
        if (status === google.maps.GeocoderStatus.OK) {
            field.latlng = results[0].geometry.location;
            field.geopt = latlng_to_obj(field.latlng);
            console.log("Geocode done: " + this.latlng.toString() + " => " + this.geopt);
            bridge.setValue(object, this.value);
        }
    });
    bridge.setValue(object, this.value);
};


com.sweattrails.api.GeocodeField.prototype.renderView = function(value) {
    var ret = document.createElement("div");
    ret.id = "mapview-" + this.field.id;
    if (value) {
        var job = {
            mapdiv: ret,
            field: this,
            value: value,
            run: function() {
                var latlng = obj_to_latlng(this.value);
                console.log("Rendering geopt: " + this.value + " => " + latlng.toString());
                this.mapdiv.style.width = "160px";
                this.mapdiv.style.height = "160px";
                var mapOptions = {
                    zoom: 8,
                    center: latlng,
                    mapTypeId: google.maps.MapTypeId.ROADMAP
                };
                field.map = new google.maps.Map(this.mapdiv, mapOptions);
                var marker = new google.maps.Marker({ map: field.map, position: latlng });                
            }
        };
        loadGMaps(job);
    } else {
        ret.innerHTML = "&#160;";        
    }
    return ret;
};

com.sweattrails.api.internal.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
