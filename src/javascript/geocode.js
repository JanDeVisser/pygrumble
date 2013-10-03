function obj_to_latlng(obj) {
    return new google.maps.LatLng(obj.lat, obj.lon);
}

function latlng_to_obj(latlng) {
    var ret = {
        "lat": latlng.lat(),
        "lon": latlng.lng()
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
    flush_queue("gmaps");
}

function loadGMaps(job) {
    if ((typeof(google) === "undefined") || !google.maps) {
        add_to_queue("gmaps", job);
        var script = document.createElement("script");
        script.type = "text/javascript";
        script.src = "http://maps.googleapis.com/maps/api/js?key=" + google_api_key + "&sensor=false&callback=loadGMapsCallback";
        document.body.appendChild(script);
    } else {
        execute_job(job);
    }
}

com.sweattrails.api.GeocodeField = function(fld, elem) {
    this.field = fld;
    this.latlng = null;
    this.geopt = null;
    this.width = elem.getAttribute("width") || "200px";
    this.height = elem.getAttribute("height") || "200px";
    this.size = elem.getAttribute("size") || 20;
};

com.sweattrails.api.GeocodeField.prototype.renderMap = function(value) {
    loadGMaps({
        field: this,
        value: value,
        run: function() {
            if (this.value) {
                this.field.geopt = this.value;
                this.field.latlng = obj_to_latlng(this.value);
                if (this.field.map) {
                    this.field.map.setCenter(this.field.latlng);
                } else {
                    this.field.mapdiv.style.width = this.field.width;
                    this.field.mapdiv.style.height = this.field.height;
                    var mapOptions = {
                        zoom: 16,
                        center: this.field.latlng,
                        mapTypeId: google.maps.MapTypeId.ROADMAP
                    };
                    this.field.map = new google.maps.Map(this.field.mapdiv, mapOptions);
                }
                var marker = new google.maps.Marker({ map: this.field.map, position: this.field.latlng });
            }
        }
    });    
};

com.sweattrails.api.GeocodeField.prototype.lookup = function(value) {
    loadGMaps({
        field: this,
        value: value,
        handleResult: function(results, status) {
            if (status === google.maps.GeocoderStatus.OK) {
                var latlng = results[0].geometry.location;
                var obj = latlng_to_obj(latlng);
                this.field.renderMap(obj);
            }            
        },        
        run: function() {
            new google.maps.Geocoder().geocode({'address': this.value}, this.handleResult.bind(this));
        }
    });
};

com.sweattrails.api.GeocodeField.prototype.renderEdit = function(value) {
    var ret = document.createElement("div");
    ret.id = "edit-geocode-" + this.field.id;
    this.map = null;
    var span = document.createElement("span");
    ret.appendChild(span);
    this.search = document.createElement("input");
    this.search.id = "search-" + this.field.id;
    this.search.type = "search";
    this.search.size = this.size;
    span.appendChild(this.search);
    this.button = document.createElement("input");
    this.button.field = this;
    this.button.id = "button-" + this.field.id;
    this.button.type = "button";
    this.button.value = "Look up";
    this.button.onclick = function() {
        this.field.lookup(this.field.search.value);
    };
    span.appendChild(this.button);
    this.mapdiv = document.createElement("div");
    this.mapdiv.id = "mapview-" + this.field.id;
    ret.appendChild(this.mapdiv);
    if (value) {
        this.renderMap(value);
    }
    return ret;
};

com.sweattrails.api.GeocodeField.prototype.setValueFromControl = function(bridge, object) {
    bridge.setValue(object, this.geopt || null);
};


com.sweattrails.api.GeocodeField.prototype.renderView = function(value) {
    this.map = null;
    this.mapdiv = document.createElement("div");
    this.mapdiv.id = "mapview-" + this.field.id;
    if (value) {
        this.renderMap(value);
    } else {
        this.mapdiv.innerHTML = /* "&#160;"; */ "<i><small>... Location not set ...</small></i>";
    }
    return this.mapdiv;
};

com.sweattrails.api.internal.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
