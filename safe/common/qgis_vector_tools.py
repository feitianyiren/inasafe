
"""**Utilities around QgsVectorLayer**
"""

__author__ = 'Dmitry Kolesov <kolesov.dm@gmail.com>'
__revision__ = '$Format:%H$'
__date__ = '14/01/2014'
__license__ = "GPL"
__copyright__ = 'Copyright 2012, Australia Indonesia Facility for '
__copyright__ += 'Disaster Reduction'


from safe.storage.raster import qgis_imported
from safe.common.exceptions import WrongDataTypeException

if qgis_imported:   # Import QgsRasterLayer if qgis is available
    from PyQt4.QtCore import QVariant
    from qgis.core import (
        QgsField,
        QgsVectorLayer,
        QgsFeature,
        QgsPoint,
        QgsGeometry,
        QgsFeatureRequest
    )


def points_to_rectangles(points, dx, dy):
    """Create polygon layer around points. The polygons are dx to dy.
    Attributes of the points are copied.
    A point position is upper-left corner of the created rectangle.

    :param points:  Point layer.
    :type points:   QgsVectorLayer

    :param dx:      Length of the horizontal sides
    :type dx:       float

    :param dy:      Length of the vertical sides
    :type dy:       float

    :returns:       Polygon layer
    :rtype:         QgsVectorLayer
    """

    crs = points.crs().toWkt()
    point_provider = points.dataProvider()
    fields = point_provider.fields()

    # Create layer for store the lines from E and extent
    polygons = QgsVectorLayer(
        'Polygon?crs=' + crs, 'polygons', 'memory')
    polygon_provider = polygons.dataProvider()

    polygon_provider.addAttributes(fields.toList())
    polygons.startEditing()
    for feature in points.getFeatures():
        attrs = feature.attributes()
        point = feature.geometry().asPoint()
        x, y = point.x(), point.y()
        g = QgsGeometry.fromPolygon([
            [QgsPoint(x, y),
             QgsPoint(x + dx, y),
             QgsPoint(x + dx, y - dy),
             QgsPoint(x, y - dy)]
        ])
        polygon_feat = QgsFeature()
        polygon_feat.setGeometry(g)
        polygon_feat.setAttributes(attrs)
        _ = polygon_provider.addFeatures([polygon_feat])
    polygons.commitChanges()

    return polygons


def union_geometry(vector, request=QgsFeatureRequest()):
    """Return union of the vector geometries regardless of the attributes.
    (If request is specified, filter the objects before union).
    If all geometries in the vector are invalid, return None.

    The boundaries will be dissolved during the operation.

    :param vector:  Vector layer
    :type vector:   QgsVectorLayer

    :param request: Filter for vector objects
    :type request:  QgsFeatureRequest

    :return:        Union of the geometry
    :rtype:         QgsGeometry or None
    """

    result_geometry = None
    for feature in vector.getFeatures(request):
        if result_geometry is None:
            result_geometry = QgsGeometry(feature.geometry())
        else:
            # But some feature.geometry() may be invalid, skip them
            tmp_geometry = result_geometry.combine(feature.geometry())
            try:
                if tmp_geometry.isGeosValid():
                    result_geometry = tmp_geometry
            except AttributeError:
                pass
    return result_geometry


def split_by_polygon(
        vector,
        polygon,
        request=QgsFeatureRequest(),
        mark_value=None):
    """Split objects from vector layer by polygon.

    If request is specified, filter the objects before splitting.

    If part of vector object lies in the polygon, mark it by mark_value (
    optional).

    :param vector:  Vector layer
    :type vector:   QgsVectorLayer

    :param polygon: Splitting polygon
    :type polygon:  QgsGeometry

    :param request: Filter for vector objects
    :type request:  QgsFeatureRequest

    :param mark_value:  Field value to mark the objects.
    :type mark_value:   (field_name, field_value).or None

    :returns: Vector layer with split geometry
    :rtype: QgsVectorLayer
    """

    def _set_feature(geometry, attributes):
        """
        Helper to create and set up feature
        """
        included_feature = QgsFeature()
        included_feature.setGeometry(geometry)
        included_feature.setAttributes(attributes)
        return included_feature

    def _update_attr_list(attributes, index, value, add_attribute=False):
        """
        Helper for update list of attributes.
        """
        new_attributes = attributes[:]
        if add_attribute:
            new_attributes.append(value)
        else:
            new_attributes[index] = value
        return new_attributes

    # Create layer to store the splitted objects
    crs = vector.crs().toWkt()
    if vector.geometryType() == 0:
        msg = "Points cant' be split"
        raise WrongDataTypeException(msg)
    elif vector.geometryType() == 1:
        uri = 'LineString?crs=' + crs
    elif vector.geometryType() == 2:
        uri = 'Polygon?crs=' + crs
    else:
        msg = "Received unexpected type of layer geometry: %s" \
              % (vector.geometryType(),)
        raise WrongDataTypeException(msg)

    result_layer = QgsVectorLayer(uri, 'intersected', 'memory')
    result_provider = result_layer.dataProvider()
    result_layer.startEditing()
    # Copy fields from vector
    vector_provider = vector.dataProvider()
    fields = vector_provider.fields()
    result_provider.addAttributes(fields.toList())
    # If target_field does not exist, add it:
    new_field_added = False
    if mark_value is not None:
        target_field = mark_value[0]
        if fields.indexFromName(target_field) == -1:
            result_provider.addAttributes(
                [QgsField(target_field, QVariant.Int)])
            new_field_added = True

    result_layer.commitChanges()
    target_value = None

    if mark_value is not None:
        target_field = mark_value[0]
        target_value = mark_value[1]
        target_field_index = result_provider.fieldNameIndex(target_field)
        if target_field_index == -1:
            raise WrongDataTypeException(
                'Field not found for %s' % target_field)

    # Start split procedure
    for initial_feature in vector.getFeatures(request):
        initial_geom = initial_feature.geometry()
        attributes = initial_feature.attributes()
        geometry_type = initial_geom.type()
        if polygon.intersects(initial_geom):
            # Find parts of initial_geom, intersecting
            # with the polygon, then mark them if needed
            intersection = QgsGeometry(
                initial_geom.intersection(polygon)
            ).asGeometryCollection()

            for g in intersection:
                if g.type() == geometry_type:
                    if mark_value is not None:
                        new_attributes = _update_attr_list(
                            attributes,
                            target_field_index,
                            target_value,
                            add_attribute=new_field_added
                        )
                    feature = _set_feature(g, new_attributes)
                    _ = result_layer.dataProvider().addFeatures([feature])

            # Find parts of the initial_geom that do not lies in the polygon
            diff_geom = QgsGeometry(
                initial_geom.symDifference(polygon)
            ).asGeometryCollection()
            for g in diff_geom:
                if g.type() == geometry_type:
                    new_attributes = _update_attr_list(
                        attributes,
                        target_field_index,
                        0,
                        add_attribute=new_field_added
                    )
                    feature = _set_feature(g, new_attributes)
                    _ = result_layer.dataProvider().addFeatures([feature])
        else:
            if mark_value is not None:
                new_attributes = _update_attr_list(
                    attributes,
                    target_field_index,
                    0,
                    add_attribute=new_field_added
                )
            feature = _set_feature(initial_geom, new_attributes)
            _ = result_layer.dataProvider().addFeatures([feature])
    result_layer.commitChanges()
    result_layer.updateExtents()

    return result_layer
