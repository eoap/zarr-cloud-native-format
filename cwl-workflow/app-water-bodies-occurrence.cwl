cwlVersion: v1.0
$namespaces:
  s: https://schema.org/
s:softwareVersion: 1.1.0
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

  - class: CommandLineTool
    id: occurrence
    label: Water bodies occurrence
    doc: Water bodies occurrence based on NDWI and otsu threshold
    hints:
      DockerRequirement:
        dockerPull: occ:latest
    requirements:
      - class: EnvVarRequirement
        envDef:
          PYTHONPATH: /app
      - class: ResourceRequirement
        coresMax: 1
        ramMax: 512
    baseCommand: ["python", "-m", "app"]
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