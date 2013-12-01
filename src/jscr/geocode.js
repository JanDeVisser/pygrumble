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

com.sweattrails.api.GeocodeField.prototype.renderMap = function(value, async) {
    if (async) {
        loadGMaps({
            field: this,
            value: value,
            run: function() {
                this.field.renderMap(this.value, false);
            }
        });
    } else {
        if (value) {
            this.geopt = value;
            this.latlng = obj_to_latlng(value);
            if (!this.mapdiv) {
                this.mapdiv = document.createElement("div");
                this.mapdiv.id = "mapedit-" + this.field.id;
                this.mapdiv.style.width = this.width;
                this.mapdiv.style.height = this.height;
            }
            this.view.appendChild(this.mapdiv);
            this.mapdiv.hidden = false;
            if (this.map) {
                this.map.setCenter(this.latlng);
            } else {
                var mapOptions = {
                    zoom: 16,
                    center: this.latlng,
                    mapTypeId: google.maps.MapTypeId.ROADMAP
                };
                this.map = new google.maps.Map(this.mapdiv, mapOptions);
            }
            var marker = new google.maps.Marker({ map: this.map, position: this.latlng });
        }
    }
};

com.sweattrails.api.GeocodeField.prototype.lookup = function(value) {
    loadGMaps({
        field: this,
        value: value,
        handleResult: function(results, status) {
            if (status === google.maps.GeocoderStatus.OK) {
                var latlng = results[0].geometry.location;
                var obj = latlng_to_obj(latlng);
                this.field.renderMap(obj, false);
            }            
        },        
        run: function() {
            new google.maps.Geocoder().geocode({'address': this.value}, this.handleResult.bind(this));
        }
    });
};

com.sweattrails.api.GeocodeField.prototype.renderEdit = function(value) {
    this.view = document.createElement("div");
    this.view.id = "edit-geocode-" + this.field.id;
    var span = document.createElement("span");
    this.view.appendChild(span);
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
    if (value) {
        this.renderMap(value, true);
    }
    return this.view;
};

com.sweattrails.api.GeocodeField.prototype.setValueFromControl = function(bridge, object) {
    bridge.setValue(object, this.geopt || null);
};


com.sweattrails.api.GeocodeField.prototype.renderView = function(value) {
    this.view = document.createElement("div");
    this.view.id = "view-geocode-" + this.field.id;
    if (value) {
        this.renderMap(value, true);
    } else {
        this.view.innerHTML = /* "&#160;"; */ "<i><small>... Location not set ...</small></i>";
    }
    return this.view;
};

com.sweattrails.api.GeocodeField.prototype.erase = function() {
    if (this.mapdiv) {
        this.mapdiv.hidden = true;
        document.body.appendChild(this.mapdiv);
    }
};

com.sweattrails.api.GeocodeField.prototype.clear = function() {
    this.setValue("");
};

com.sweattrails.api.GeocodeField.prototype.setValue = function(value) {
    console.log("setValue not implemented for GeocodeField...");
};

com.sweattrails.api.internal.fieldtypes.geocode = com.sweattrails.api.GeocodeField;
