"""
export_handlers.py
Generate KML and GPX files from telemetry data.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict

def to_kml(trajectory: List[Dict], name: str = "TuniLoon Flight") -> str:
    """
    Generate KML (Google Earth) from telemetry data.
    """
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    doc = ET.SubElement(kml, 'Document')
    ET.SubElement(doc, 'name').text = name

    # Style for path
    style = ET.SubElement(doc, 'Style', id='pathStyle')
    line = ET.SubElement(style, 'LineStyle')
    ET.SubElement(line, 'color').text = 'ff6b35'  # ABGR format
    ET.SubElement(line, 'width').text = '3'

    # Placemark for path
    pm = ET.SubElement(doc, 'Placemark')
    ET.SubElement(pm, 'name').text = f'{name} Path'
    ET.SubElement(pm, 'styleUrl').text = '#pathStyle'
    line_string = ET.SubElement(pm, 'LineString')
    ET.SubElement(line_string, 'extrude').text = '1'
    ET.SubElement(line_string, 'tessellate').text = '1'
    coords = ET.SubElement(line_string, 'coordinates')
    coord_str = '\n'.join(
        f"{p['longitude']},{p['latitude']},{p['altitude']}"
        for p in trajectory
    )
    coords.text = coord_str

    # Placemarks for launch and landing
    launch = trajectory[0]
    landing = trajectory[-1]
    for label, point, color in [
        ('Launch', launch, 'green'),
        ('Landing', landing, 'red')
    ]:
        pm2 = ET.SubElement(doc, 'Placemark')
        ET.SubElement(pm2, 'name').text = label
        point_elem = ET.SubElement(pm2, 'Point')
        coords_elem = ET.SubElement(point_elem, 'coordinates')
        coords_elem.text = f"{point['longitude']},{point['latitude']},{point['altitude']}"
        style2 = ET.SubElement(pm2, 'Style')
        icon = ET.SubElement(style2, 'IconStyle')
        ET.SubElement(icon, 'color').text = color
        ET.SubElement(icon, 'scale').text = '1.5'

    return ET.tostring(kml, encoding='unicode', method='xml')

def to_gpx(trajectory: List[Dict], name: str = "TuniLoon Flight") -> str:
    """
    Generate GPX (GPS Exchange Format) from telemetry data.
    """
    gpx = ET.Element('gpx', version='1.1',
                     creator='TuniLoon',
                     xmlns='http://www.topografix.com/GPX/1/1')

    # Metadata
    metadata = ET.SubElement(gpx, 'metadata')
    ET.SubElement(metadata, 'name').text = name
    ET.SubElement(metadata, 'time').text = datetime.now().isoformat()

    # Track
    trk = ET.SubElement(gpx, 'trk')
    ET.SubElement(trk, 'name').text = name
    seg = ET.SubElement(trk, 'trkseg')

    for p in trajectory:
        trkpt = ET.SubElement(seg, 'trkpt',
                              lat=str(p['latitude']),
                              lon=str(p['longitude']))
        ET.SubElement(trkpt, 'ele').text = str(p['altitude'])
        ET.SubElement(trkpt, 'time').text = datetime.now().isoformat()

    return ET.tostring(gpx, encoding='unicode', method='xml')
