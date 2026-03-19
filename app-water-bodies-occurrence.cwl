cwlVersion: v1.0
$namespaces:
  s: https://schema.org/
s:softwareVersion: 1.1.0
s:name: Water bodies occurrence workflow
s:description: Water bodies occurrence based on NDWI and otsu threshold
s:dateCreated: "2026-03-19"
s:license: https://spdx.org/licenses/MIT.html
s:softwareHelp:
  class: s:CreativeWork
  s:name: Zarr Cloud-Native Format documentation
  s:url: https://eoap.github.io/zarr-cloud-native-format/
s:publisher:
  class: s:Organization
  s:name: EOAP
s:author:
  - class: s:Person
    s:givenName: Fabrice
    s:familyName: Brito
    s:email: info@terradue.com
    s:affiliation:
      class: s:Organization
      s:name: Terradue
s:codeRepository:
  URL: https://github.com/eoap/zarr-cloud-native-format.git
schemas:
  - http://schema.org/version/9.0/schemaorg-current-http.rdf
$graph:
  - class: Workflow
    id: water-bodies-occurrence
    label: Water bodies occurrence
    doc: Water bodies occurrence based on NDWI and otsu threshold
    requirements: []
    inputs:
      zarr-stac-catalog:
        type: Directory
        doc: Input STAC catalog with datacube
        label: Zarr store STAC Catalog
    outputs:
      stac-catalog:
        type: Directory
        outputSource: 
        - step_occurrence/stac-catalog
        doc: Output STAC catalog with water bodies occurrence
        label: STAC catalog
    steps:
      step_occurrence:
        label: Water bodies occurrence
        doc: Water bodies occurrence based on NDWI and otsu threshold
        run: "#occurrence"
        in:
          zarr-stac-catalog: zarr-stac-catalog
        out: 
          - stac-catalog

  - class: Workflow
    id: water-bodies
    label: Water bodies occurrence
    doc: Water bodies occurrence based on NDWI and otsu threshold
    requirements: []
    inputs:
      zarr-stac-catalog:
        type: Directory
        doc: Input STAC catalog with datacube
        label: Zarr store STAC Catalog
    outputs:
      stac-catalog:
        type: Directory
        outputSource:
        - step_occurrence/stac-catalog
        doc: Output STAC catalog with water bodies occurrence
        label: STAC catalog
    steps:
      step_occurrence:
        label: Water bodies occurrence
        doc: Water bodies occurrence based on NDWI and otsu threshold
        run: "#occurrence"
        in:
          zarr-stac-catalog: zarr-stac-catalog
        out:
          - stac-catalog

  - class: CommandLineTool
    id: occurrence
    label: Water bodies occurrence
    doc: Water bodies occurrence based on NDWI and otsu threshold
    hints:
      DockerRequirement:
        dockerPull: occurrence:latest
    requirements:
      ResourceRequirement:
        coresMax: 1
        ramMin: 512
        ramMax: 1024
    baseCommand: ["occurrence"]
    arguments: []
    inputs:
      zarr-stac-catalog:
        type: Directory
        inputBinding:
          prefix: --stac-catalog
    outputs:
      stac-catalog:    
        outputBinding:
          glob: '.'
        type: Directory
