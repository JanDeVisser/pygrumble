/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

//
// ---------------------------------------------------------------------------
//
// P R O F I L E
//
// ---------------------------------------------------------------------------
//

//
// ---------------------------------------------------------------------------
//
// S E S S I O N S
//
// ---------------------------------------------------------------------------
//

function makeSessionLink(data) {
    var ret = new com.sweattrails.api.Link(
                (data.description != "") ? data.description : "<i>Untitled</i>",
                "/session")
    ret.parameter("id", data.key)
    return ret
}

//
// ---------------------------------------------------------------------------
//
// S E S S I O N  U P L O A D
//
// ---------------------------------------------------------------------------
//

function upload(/*event*/) {
    $$.form.upload.popup(com.sweattrails.api.MODE_NEW)
}

function uploadChoices() {
    menu = document.createElement("div");
    div = document.createElement("div");
    menu.appendChild(div);
    a = document.createElement("a");
    div.appendChild(a);
    a.href="#";
    a.className = "menulink";
    a.onclick = uploadPowertap;
    a.innerHTML = "Powertap";
    item = document.getElementById("upload_choice");
    bar = document.getElementById("sessions_menu");
    menu.id = "upload_menu";
    menu.style.position = "absolute";
    menu.style.top = 77; //item.offsetTop + item.offsetHeight;
    menu.style.left = item.offsetLeft;
    menu.style.backgroundColor = "white";
    menu.style.border = "thin solid black";
    menu.style.padding = "5px";
    menu.style.marginLeft = "0px";
    menu.style.marginTop = "0px";
    menu.style.marginBottom = "5px";
    item.appendChild(menu);
    menu.hidden = false;
}

function inspectFile(ev) {
    var data = this.result;
    var form = $$.form.upload
    if (data.match(/^Minutes,/)) {
        // File is a standard CSV export
        // Need time and description
        form.progressOff()
        form.$.description.hidden = false
        form.$.timestamp.hidden = false
        form.datasource.object.filetype = "CSV"
        var re = /\w+\s(\d{4})-(\d{2})-(\d{2})\s(\d{2})-(\d{2})-\d{2}\.csv/
        var fname = form.datasource.object.filename
        if ((res = re.exec(fname)) != null) {
            console.log("fname: " + fname + " RE: " + res[1] + " " + res[2] + " " + res[3] + " " + res[4] + " " + res[5])
            var d = { year: parseInt(res[1], 10), month: parseInt(res[3], 10), day: parseInt(res[2], 10),
                hour: parseInt(res[4], 10), minute: parseInt(res[5], 10) }
            form.datasource.object.timestamp = d
            form.$.timestamp.render("new", form.datasource.object)
        }
    } else if (data.match(/^Version,Date\/Time,Km,Minutes,/)) {
        // File is an extended CSV export
        // Need description
        form.progressOff()
        form.$.description.hidden = false
        form.$.timestamp.hidden = true
        form.datasource.object.filetype = "CSV"
    } else if (data.match(/http:\/\/www.garmin.com\/xmlschemas\/TrainingCenterDatabase\/v2/)) {
        // File is a garmin TCX export
        // Need description
        form.progressOff()
        form.$.description.hidden = false
        form.$.timestamp.hidden = true
        form.datasource.object.filetype = "TCX"
    } else if (data.match(/http:\/\/www.topografix.com\/GPX\/1\/1/)) {
        // File is a garmin GPX export - has name and description
        form.progressOff()
        form.$.description.hidden = true
        form.$.timestamp.hidden = true
        form.datasource.object.filetype = "GPX"
    } else {
        // Unknown file type:
        form.error("Unknown file type")
        form.$.description.hidden = false
        form.$.timestamp.hidden = false
        form.datasource.object.filetype = ""
    }
}

function fileSelected(datafile) {
    this.form.datasource.object.filename = datafile.name
    var reader = new FileReader()
    reader.onload = inspectFile;
    reader.readAsText(datafile.slice(0, 1000));
}

function showError(status) {
    $$.form.upload.error("Error processing file: " + status)
}

function commitSent() {
    $$.form.upload.close()
}

function sendCommit() {
    var form = $$.form.upload
    var req = new ST.JSONRequest("/upload/file/commit", commitSent, showError)
    req.post = true
    req.parameter("key", form.datasource.object.curfile.key)
    req.parameter('async', 'n')
    req.execute()
}

function blockSent() {
    var form = $$.form.upload
    if (form.datasource.object.curfile.line_ix < form.datasource.object.curfile.lines.length) {
        form.datasource.object.curfile.block += 1
        form.progress("Sent block " + form.datasource.object.curfile.block)
        sendBlock()
    } else {
        form.progress("Committing upload")
        sendCommit()
    }
}

function sendBlock() {
    var form = $$.form.upload
    var size = form.datasource.object.curfile.lines.length - form.datasource.object.curfile.line_ix
    if (size > 900) size = 900
    var end = form.datasource.object.curfile.line_ix + size;

    var req = new ST.JSONRequest("/upload/file/data", blockSent, showError)
    req.parameter("key", form.datasource.object.curfile.key)
    var data = ""
    for (; form.datasource.object.curfile.line_ix < end; form.datasource.object.curfile.line_ix++) {
        data += form.datasource.object.curfile.lines[form.datasource.object.curfile.line_ix] + "\r\n";
    }
    req.parameter("data", data)
    req.post = true
    req.async = false
    req.execute()
}

function sendFile(ev) {
    var form = $$.form.upload
    data = this.result;
    form.datasource.object.curfile.lines = data.split(/[\r\n]|\n/)
    form.datasource.object.curfile.line_ix = 0
    sendBlock()
}

function sendFirstBlock(resp) {
    var form = $$.form.upload
    form.progress("Upload initiated")
    form.datasource.object.curfile.key = resp.datafile
    form.datasource.object.curfile.block = 0
    var reader = new FileReader()
    form.datasource.object.curfile.name = form.datasource.object.datafile.name
    reader.onload = sendFile;
    reader.readAsText(form.datasource.object.datafile);
}

function startUpload() {
    var form = $$.form.upload
    form.applyData()
    var req = new com.sweattrails.api.JSONRequest("/upload/file/begin", sendFirstBlock, showError)
    req.parameter("filetype", form.datasource.object.filetype)
    req.parameter("description", form.datasource.object.description)
    var d = form.datasource.object.timestamp
    if (d.year) {
        req.parameter("ts_month", d.month)
        req.parameter("ts_day", d.day)
        req.parameter("ts_year", d.year)
        req.parameter("ts_hour", d.hour)
        req.parameter("ts_minute", d.minute)
    }
    req.post = true
    form.datasource.object.curfile = {}
    req.execute()
}

//
// ---------------------------------------------------------------------------
//
// F I T N E S S
//
// ---------------------------------------------------------------------------
//

function updateFTP() {
    $$.table.ftphistory.openForm()
}

function renderFTPTable() {
    $$.table.ftphistory.render()
}

function showCurrentFTP() {
    var curftp_span = document.getElementById("current_ftp")
    if (_.current_ftp) {
        var curftp = _.current_ftp
        curftp_span.innerHTML = curftp.power + "W"
    } else {
        curftp_span.innerHTML = ""
        document.getElementById("update_ftp_link").innerHTML = "Set it now"
    }
}

function setCurrentFTP(data) {
    _.current_ftp = (data.length > 0) && data[0]
}

//
// ---------------------------------------------------------------------------
//
// H I S T O R Y
//
// ---------------------------------------------------------------------------
//

function addHistoryEntry() {
    $$.form.healthhistory.popup(com.sweattrails.api.MODE_NEW)
}

function renderHistoryTable() {
    $$.table.history.render()
}


//
// ---------------------------------------------------------------------------
//
// G E A R  T Y P E S
//
// ---------------------------------------------------------------------------
//

function init_new_sub_gt() {
    var gt = {}
    gt.isA = this.datasource.data
    gt.usedFor = this.datasource.data.usedFor
    gt.partOf = this.datasource.data.partOf
    return st
}

function new_sub_gt(form, action) {
    form.render(com.sweattrails.api.MODE_NEW)
}

//
// ---------------------------------------------------------------------------
//
// S E S S I O N  T Y P E S
//
// ---------------------------------------------------------------------------
//

function init_new_sub_st() {
    var st = {}
    st.subTypeOf = this.datasource.data
    st.trackDistance = this.datasource.data.trackDistance
    st.speedPace = this.datasource.data.speedPace
    return st
}

function new_sub_st(form, action) {
    form.render(com.sweattrails.api.MODE_NEW)
}
