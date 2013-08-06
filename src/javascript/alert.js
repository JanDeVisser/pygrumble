/**
 * Alert - A modal popup window.
 */
var alert_count = 0

function st_alert(msg) {
    var id = "alert-" + alert_count
    alert_count += 1
    var alert = new com.sweattrails.api.Alert(id)
    alert.setMessage(msg)
    alert.addAction({name: "ok", action: "cancel", label: "OK"})
    alert.popup()
}

com.sweattrails.api.Alert = function(id) {
    this.id = id
    this.type = "alert"
    var body = document.getElementsByTagName("body")[0]
    this.overlay = document.getElementById("overlay")
    if (!this.overlay) {
        this.overlay = document.createElement("div")
        this.overlay.id = "overlay"
        this.overlay.className = "overlay"
        this.overlay.hidden = true
        body.appendChild(this.overlay)
    }
    var container = document.createElement("div")
    container.id = this.id + "-modal"
    container.className = "modal"
    container.hidden = true
    body.appendChild(container)
    this.container = container
    this.footer = new com.sweattrails.api.ActionContainer(this, "footer")
    com.sweattrails.api.STManager.register(this)
    return this
}

com.sweattrails.api.Alert.prototype.setMessage = function(msg) {
    this.message = msg
}

com.sweattrails.api.Alert.prototype.addAction = function(action) {
    this.footer.buildAction(action)
}

com.sweattrails.api.Alert.prototype.build = function(f) {
    this.footer.build(f)
    var msgs = getChildrenByTagNameNS(elem, com.sweattrails.api.xmlns, "message")
    if (msgs && (msgs.length > 0)) {
        for (var j = 0; j < msgs.length; j++) {
            this.message = msgs[0].innerHTML
        }
    }
}

com.sweattrails.api.Alert.prototype.render = function() {
    console.log("Alert[" + this.id + "].render() " + this.container.className)
    if (!this.container || !this.container.hidden || (this.container.className == "tabpage")) {
        this.footer.erase()
        var div = document.createElement("div")
        div.innerHTML = this.message
        this.container.appendChild(div)
        this.footer.render()
    }
}

com.sweattrails.api.Alert.prototype.submit = function() {
    this.close()
}

com.sweattrails.api.Alert.prototype.progressOff = function() {
    this.footer.progressOff()
}


com.sweattrails.api.Alert.prototype.progress = function(msg) {
    this.footer.progress(msg)
}

com.sweattrails.api.Alert.prototype.error = function(msg) {
    this.footer.error(msg)
}

com.sweattrails.api.Alert.prototype.popup = function() {
    document.getElementById("overlay").hidden = false
    this.container.hidden = false
    this.ispopup = true
    this.render()
}

com.sweattrails.api.Alert.prototype.close = function() {
    try {
        this.progressOff()
        this.container.hidden = true
        this.overlay.hidden = true
    } finally {
        this.ispopup = false
    }
}

/*
 * AlertBuilder -
 */

com.sweattrails.api.AlertBuilder = function() {
    this.type = "builder"
    this.name = "alertbuilder"
    com.sweattrails.api.STManager.processor("alert", this)
}

com.sweattrails.api.AlertBuilder.prototype.process = function(f) {
    var id = f.getAttribute("name")
    console.log("AlertBuilder: found alert " + id)
    var alert = new com.sweattrails.api.Alert(id, f.parentNode)
    alert.build(f)
}

new com.sweattrails.api.AlertBuilder()

