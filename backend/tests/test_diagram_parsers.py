from __future__ import annotations

import io
import zipfile

from app.services.diagram_parsers import parse_native_diagram_source


def test_parse_drawio_xml() -> None:
    raw = b"""
<mxGraphModel><root>
  <mxCell id="0"/><mxCell id="1" parent="0"/>
  <mxCell id="n1" value="Client" vertex="1">
    <mxGeometry x="10" y="10" width="120" height="60" as="geometry"/>
  </mxCell>
  <mxCell id="n2" value="API" vertex="1">
    <mxGeometry x="260" y="20" width="120" height="60" as="geometry"/>
  </mxCell>
  <mxCell id="e1" edge="1" source="n1" target="n2"/>
</root></mxGraphModel>
"""
    out = parse_native_diagram_source("sample.drawio", raw)
    assert out is not None
    assert len(out["nodes"]) == 2
    assert len(out["edges"]) == 1


def test_parse_mermaid_flowchart() -> None:
    raw = b"""
flowchart LR
  A[Client] --> B[API]
  B --> C[(DB)]
"""
    out = parse_native_diagram_source("x.mmd", raw)
    assert out is not None
    assert len(out["nodes"]) >= 3
    assert len(out["edges"]) >= 2


def test_parse_vsdx_minimal() -> None:
    page_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
  <Shapes>
    <Shape ID="1"><Text>Start</Text><Cell N="PinX" V="1.2"/><Cell N="PinY" V="1.1"/></Shape>
    <Shape ID="2"><Text>End</Text><Cell N="PinX" V="3.6"/><Cell N="PinY" V="1.1"/></Shape>
  </Shapes>
  <Connects>
    <Connect FromSheet="1" ToSheet="2"/>
  </Connects>
</PageContents>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("visio/pages/page1.xml", page_xml)
    out = parse_native_diagram_source("topology.vsdx", buf.getvalue())
    assert out is not None
    assert len(out["nodes"]) == 2
    assert len(out["edges"]) == 1
