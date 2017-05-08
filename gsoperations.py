# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from PyQt4 import QtCore
from qgis.core import *
from geoserverexplorer.qgis import layers as qgislayers
from geoserverexplorer.qgis.catalog import CatalogWrapper
from geoserverexplorer.gui.confirm import publishLayer
from geoserverexplorer.gui.dialogs.projectdialog import PublishProjectDialog
from geoserver.catalog import ConflictingDataError
from geoserverexplorer.gui.dialogs.layerdialog import PublishLayersDialog


def publishDraggedLayer(explorer, layer, workspace):
    cat = workspace.catalog
    cat = CatalogWrapper(cat)
    ret = explorer.run(publishLayer,
             "Publish layer from layer '" + layer.name() + "'",
             [],
             cat, layer, workspace)
    return ret

def addDraggedLayerToGroup(explorer, layer, groupItem):
    group = groupItem.element
    styles = group.styles
    layers = group.layers
    if layer.name not in layers:
        layers.append(layer.name)
        styles.append(layer.default_style.name)
    group.dirty.update(layers = layers, styles = styles)
    explorer.run(layer.catalog.save,
                 "Update group '" + group.name + "'",
                 [groupItem],
                 group)

def addDraggedUrisToWorkspace(uris, catalog, workspace, explorer, tree):
    if uris and workspace:
        allLayers = qgislayers.getAllLayersAsDict()
        publishableLayers = qgislayers.getPublishableLayersAsDict()
        if len(uris) > 1:
            explorer.setProgressMaximum(len(uris))
        for i, uri in enumerate(uris):
            source = uri if isinstance(uri, basestring) else uri.uri
            if source in allLayers:
                layer = publishableLayers.get(source, None)
            else:
                if isinstance(uri, basestring):
                    layerName = QtCore.QFileInfo(uri).completeBaseName()
                    layer = QgsRasterLayer(uri, layerName)
                else:
                    layer = QgsRasterLayer(uri.uri, uri.name)
                if not layer.isValid() or layer.type() != QgsMapLayer.RasterLayer:
                    if isinstance(uri, basestring):
                        layerName = QtCore.QFileInfo(uri).completeBaseName()
                        layer = QgsVectorLayer(uri, layerName, "ogr")
                    else:
                        layer = QgsVectorLayer(uri.uri, uri.name, uri.providerKey)
                    if not layer.isValid() or layer.type() != QgsMapLayer.VectorLayer:
                        layer.deleteLater()
                        layer = None
            if layer is None:
                name = "'%s'" % allLayers[source] if source in allLayers else "with source '%s'" % source
                explorer.setWarning("Layer %s is not valid for publication" % name)
            else:
                if not publishDraggedLayer(explorer, layer, workspace):
                    break
            explorer.setProgress(i + 1)
        explorer.resetActivity()
        return [tree.findAllItems(catalog)[0]]
    else:
        return []

def addDraggedStyleToLayer(tree, explorer, styleItem, layerItem):
    catalog = layerItem.element.catalog
    style = styleItem.element
    layer = layerItem.element
    if not hasattr(layer, "default_style") or layer.default_style is None:
        # if default style is missing, make dragged style the layer's default
        # without a default style, some GeoServer operations may fail
        layer.default_style = style
    else:
        # add to layer's additional styles
        styles = layer.styles
        styles.append(style)
        layer.styles = styles
    explorer.run(catalog.save,
             "Add style '" + style.name + "' to layer '" + layer.name + "'",
             [layerItem],
             layer)


def publishProject(tree, explorer, catalog):
    layers = qgislayers.getAllLayers()
    dlg = PublishProjectDialog(catalog)
    dlg.exec_()
    if not dlg.ok:
        return
    workspace = dlg.workspace
    groupName = dlg.groupName
    overwrite = dlg.overwrite
    explorer.setProgressMaximum(len(layers), "Publish layers")
    progress = 0
    cat = CatalogWrapper(catalog)
    for layer in layers:
        explorer.setProgress(progress)
        explorer.run(publishLayer,
                     None,
                     [],
                     cat, layer, workspace, overwrite)
        progress += 1
        explorer.setProgress(progress)
    explorer.resetActivity()
    groups = qgislayers.getGroups()
    for group in groups:
        names = [layer.name() for layer in groups[group][::-1]]
        try:
            layergroup = catalog.create_layergroup(group, names, names, getGroupBounds(groups[group]))
        except ConflictingDataError:
            layergroup = catalog.get_layergroup(group)
            layergroup.dirty.update(layers = names, styles = names)
        explorer.run(catalog.save, "Create layer group '" + group + "'",
                 [], layergroup)

    if groupName is not None:
        names = [layer.name() for layer in layers[::-1]]
        try:
            layergroup = catalog.create_layergroup(groupName, names, names, getGroupBounds(layers))
        except ConflictingDataError:
            layergroup = catalog.get_layergroup(groupName)
            layergroup.dirty.update(layers = names, styles = names)
        explorer.run(catalog.save, "Create global layer group",
                 [], layergroup)
    tree.findAllItems(catalog)[0].refreshContent(explorer)
    explorer.resetActivity()

def getGroupBounds(layers):
    bounds = None
    def addToBounds(bbox, bounds):
        if bounds is not None:
            bounds = [min(bounds[0], bbox.xMinimum()),
                        max(bounds[1], bbox.xMaximum()),
                        min(bounds[2], bbox.yMinimum()),
                        max(bounds[3], bbox.yMaximum())]
        else:
            bounds = [bbox.xMinimum(), bbox.xMaximum(),
                      bbox.yMinimum(), bbox.yMaximum()]
        return bounds

    for layer in layers:
        transform = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"))
        bounds = addToBounds(transform.transformBoundingBox(layer.extent()), bounds)

    return (str(bounds[0]), str(bounds[1]), str(bounds[2]), str(bounds[3]), "EPSG:4326")

def publishLayers(tree, explorer, catalog):
    dlg = PublishLayersDialog(catalog)
    dlg.exec_()
    if dlg.topublish is None:
        return
    cat = CatalogWrapper(catalog)
    progress = 0
    explorer.setProgressMaximum(len(dlg.topublish), "Publish layers")
    for layer, workspace, name, style, enabled, title, description in dlg.topublish:
        explorer.run(cat.publishLayer,
             None,
             [],
             layer, workspace, True, name, style, enabled, title, description)
        progress += 1
        explorer.setProgress(progress)
    catItem = tree.findAllItems(catalog)[0]
    catItem.refreshContent(explorer)
    explorer.resetActivity()
