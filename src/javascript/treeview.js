/**
 * TreeNode -
 */

com.sweattrails.api.internal.TreeNode = function(tree, parent, data) {
    this.tree = tree
    this.parent = parent
    this.div = null
    this.data = data
    this.label = tree.displayValue(data)
    this.children = []
    var c = tree.getChildren(data)
    for (var cix in c) {
        var child = c[cix]
        this.children.push(new com.sweattrails.api.internal.TreeNode(this.tree, this, child))
    }
}

com.sweattrails.api.internal.TreeNode.prototype.render = function() {
    var div = document.createElement("div")
    this.parent.div.appendChild(div)
    this.arrow = document.createElement("img")
    this.arrow.src = "/images/tree-" + ((this.children.length == 0) ? "empty" : "open") + ".png"
    this.arrow.height = this.arrow.width = 20
    if (this.children.length > 0) {
        var toggle = this.toggle.bind(this)
        this.arrow.onclick = toggle
    }
    div.appendChild(this.arrow)
    var a = document.createElement("a")
    a.href = "#"
    var openForm = this.openForm.bind(this.tree, this.data)
    a.onclick = openForm
    a.innerHTML = this.label
    div.appendChild(a)
    this.div = document.createElement("div")
    this.div.className = "treeview-daycare"
    div.appendChild(this.div)
    for (var cix in this.children) {
        this.children[cix].render()
    }
}

com.sweattrails.api.internal.TreeNode.prototype.openForm = function(object) {
    if (!this.form.ispopup) {
        this.data = object
        this.form.popup()
    }
}

com.sweattrails.api.internal.TreeNode.prototype.toggle = function() {
    this.div.hidden = !this.div.hidden
    this.arrow.src = "/images/tree-" + ((this.div.hidden) ? "closed" : "open") + ".png"
}

com.sweattrails.api.internal.TreeNode.prototype.collapseExpand = function(expand) {
    if (this.children.length > 0) {
        if (this.div.hidden == expand) this.toggle()
        for (var cix in this.children) {
            this.children[cix].collapseExpand(expand)
        }
    }
}

com.sweattrails.api.internal.CollapseExpandAction = function(expand) {
    this.expand = expand

}

com.sweattrails.api.internal.CollapseExpandAction.prototype.onClick = function() {
    this.action.owner.collapseExpand(this.expand)
}

/**
 * TreeView -
 */

com.sweattrails.api.TreeView = function(id, container, ds) {
    this.container = container
    this.id = id
    this.type = "treeview"
    com.sweattrails.api.STManager.register(this)
    this.nodes = []
    this.actions = new com.sweattrails.api.ActionContainer(this)
    this.actions.add(new com.sweattrails.api.Action("expand", "Expand",
        new com.sweattrails.api.internal.CollapseExpandAction(true)))
    this.actions.add(new com.sweattrails.api.Action("collapse", "Collapse",
        new com.sweattrails.api.internal.CollapseExpandAction(false)))
    if (arguments.length > 2) {
        this.setDataSource(arguments[2])
    }
    this.childrenBridge = new com.sweattrails.api.internal.DataBridge()
    this.displayBridge = new com.sweattrails.api.internal.DataBridge()
    return this
}

com.sweattrails.api.TreeView.prototype.setDataSource = function(ds) {
    this.datasource = ds
    ds.addView(this)
}


com.sweattrails.api.TreeView.prototype.children = function(c) {
    this.childrenBridge.get = c
    if (this.div) {
        this.render()
    }
}

com.sweattrails.api.TreeView.prototype.display = function(d) {
    this.displayBridge.get = d
    if (this.div) {
        this.render()
    }
}

com.sweattrails.api.TreeView.prototype.getChildren = function(data) {
    var ret = this.childrenBridge.getValue(data)
    if (ret == null) {
        ret = []
    } else if (!Array.isArray(ret)) {
        ret = [ret]
    }
    return ret
}

com.sweattrails.api.TreeView.prototype.displayValue = function(data) {
    return this.displayBridge.getValue(data)
}

com.sweattrails.api.TreeView.prototype.render = function() {
    console.log("TreeView(" + this.id + ").render()")
    if (this.div != null) {
        this.container.removeChild(this.div)
    }
    this.datasource.reset()
    this.div = document.createElement("div")
    this.div.id = this.id + "-div"
    this.nodes = []
    this.container.appendChild(this.div)
    this.actions.render()
    this.datasource.execute()
}

com.sweattrails.api.internal.TreeNode.prototype.openForm = function(object) {
    if (!this.form.ispopup) {
        this.data = object
        this.form.popup((object == null) ? com.sweattrails.api.MODE_NEW : com.sweattrails.api.MODE_VIEW)
    }
}

com.sweattrails.api.TreeView.prototype.initForm = function() {
    this.form = new com.sweattrails.api.Form("treeview-" + this.id, this.container,
        new com.sweattrails.api.ProxyDataSource(this), true)
}

com.sweattrails.api.TreeView.prototype.noData = function() {
    this.div.innerHTML = "&#160;<i>No data</i>"
}

com.sweattrails.api.TreeView.prototype.renderData = function(obj) {
    var node = new com.sweattrails.api.internal.TreeNode(this, this, obj)
    this.nodes.push(node)
    node.render()
}

com.sweattrails.api.TreeView.prototype.reset = function(data) {
    this.nodes = []
    this.datasource.reset(data)
    this.render()
}

com.sweattrails.api.TreeView.prototype.collapseExpand = function(expand) {
    for (var nix in this.nodes) {
        this.nodes[nix].collapseExpand(expand)
    }
}

com.sweattrails.api.TreeView.prototype.getProxyData = function() {
    return this.data
}

com.sweattrails.api.TreeView.prototype.submitProxyData = function(data) {
    this.datasource.object = data
    this.datasource.submit()
}

com.sweattrails.api.TreeView.prototype.onDataSubmitted = function() {
    this.form && this.form.ispopup && this.form.onDataSubmitted()
    this.onsubmitted && this.onsubmitted()
}

com.sweattrails.api.TreeView.prototype.onDataError = function(errorinfo) {
    this.form && this.form.ispopup && this.form.onDataError(errorinfo)
    this.onerror && this.onerror(errorinfo)
}

/**
 * TreeViewBuilder -
 */

com.sweattrails.api.TreeViewBuilder = function() {
    this.type = "builder"
    this.name = "treebuilder"
    com.sweattrails.api.STManager.processor("treeview", this)
}

com.sweattrails.api.TreeViewBuilder.prototype.process = function(t) {
    var name = t.getAttribute("name")
    console.log("treeViewBuilder: building " + name)
    var ds = com.sweattrails.api.dataSourceBuilder.build(t)
    var tree = new com.sweattrails.api.TreeView(name, t.parentNode, ds)
    tree.display(t.getAttribute("display"))
    tree.children(t.getAttribute("children"))
    tree.actions.build(t)
    var nodes = getChildrenByTagNameNS(t, com.sweattrails.api.xmlns, "dataform")
    if (nodes.length == 1) {
        var nodeelem = nodes[0]
        tree.initForm()
        _.formbuilder.buildForm(tree.form, nodeelem)
    }
}

new com.sweattrails.api.TreeViewBuilder()
