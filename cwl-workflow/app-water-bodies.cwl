cwlVersion: v1.0
$namespaces:
  s: https://schema.org/
s:softwareVersion: 1.1.0
schemas:
  - http://schema.org/version/9.0/schemaorg-current-http.rdf
$graph:
  - class: Workflow
    id: water-bodies
    label: Water bodies detection based on NDWI and otsu threshold
    doc: Water bodies detection based on NDWI and otsu threshold applied to Sentinel-2 COG STAC items
    requirements:
      - class: ScatterFeatureRequirement
      - class: SubworkflowFeatureRequirement
    inputs:
      aoi:
        label: area of interest
        doc: area of interest as a bounding box
        type: string
      epsg:
        label: EPSG code
        doc: EPSG code
        type: string
        default: "EPSG:4326"
      stac_items:
        label: Sentinel-2 STAC items
        doc: list of Sentinel-2 COG STAC items
        type: string[]
      bands:
        label: bands used for the NDWI
        doc: bands used for the NDWI
        type: string[]
        default: ["green", "nir"]
    outputs:
      - id: stac_catalog
        outputSource:
          - node_stac_zarr/zarr_stac_catalog
        type: Directory
    steps:
      node_water_bodies:
        run: "#detect_water_body"
        in:
          item: stac_items
          aoi: aoi
          epsg: epsg
          bands: bands
        out:
          - detected_water_body
        scatter: item
        scatterMethod: dotproduct
      node_stac:
        run: "#stac"
        in:
          item: stac_items
          rasters:
            source: node_water_bodies/detected_water_body
        out:
          - temp_stac_catalog
      node_stac_zarr:
        run: "#stac-zarr"
        in:
          stac_catalog:
            source: node_stac/temp_stac_catalog
        out:
          - zarr_stac_catalog
  - class: Workflow
    id: detect_water_body
    label: Water body detection based on NDWI and otsu threshold
    doc: Water body detection based on NDWI and otsu threshold
    requirements:
      - class: ScatterFeatureRequirement
    inputs:
      aoi:
        doc: area of interest as a bounding box
        type: string
      epsg:
        doc: EPSG code
        type: string
        default: "EPSG:4326"
      bands:
        doc: bands used for the NDWI
        type: string[]
      item:
        doc: STAC item
        type: string
    outputs:
      - id: detected_water_body
        outputSource:
          - node_otsu/binary_mask_item
        type: File
    steps:
      node_crop:
        run: "#crop"
        in:
          item: item
          aoi: aoi
          epsg: epsg
          band: bands
        out:
          - cropped
        scatter: band
        scatterMethod: dotproduct
      node_normalized_difference:
        run: "#norm_diff"
        in:
          rasters:
            source: node_crop/cropped
        out:
          - ndwi
      node_otsu:
        run: "#otsu"
        in:
          raster:
            source: node_normalized_difference/ndwi
        out:
          - binary_mask_item
  - class: CommandLineTool
    id: crop
    requirements:
      InlineJavascriptRequirement: {}
      EnvVarRequirement:
        envDef:
          PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          PYTHONPATH: /app
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: ghcr.io/eoap/mastering-app-package/crop@sha256:324a0735cc4998f3f790c0e9b7a7df28e8ce8987d5f0798bd2d63c0e72d17dca
    baseCommand: ["python", "-m", "app"]
    arguments: []
    inputs:
      item:
        type: string
        inputBinding:
          prefix: --input-item
      aoi:
        type: string
        inputBinding:
          prefix: --aoi
      epsg:
        type: string
        inputBinding:
          prefix: --epsg
      band:
        type: string
        inputBinding:
          prefix: --band
    outputs:
      cropped:
        outputBinding:
          glob: '*.tif'
        type: File
  - class: CommandLineTool
    id: norm_diff
    requirements:
      InlineJavascriptRequirement: {}
      EnvVarRequirement:
        envDef:
          PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          PYTHONPATH: /app
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: ghcr.io/eoap/mastering-app-package/norm_diff@sha256:632991ef2c15e98c46cfa1ac7dd35a638bbe4e5c434d7503a76cf3570b17383f
    baseCommand: ["python", "-m", "app"]
    arguments: []
    inputs:
      rasters:
        type: File[]
        inputBinding:
          position: 1
    outputs:
      ndwi:
        outputBinding:
          glob: '*.tif'
        type: File
  - class: CommandLineTool
    id: otsu
    requirements:
      InlineJavascriptRequirement: {}
      EnvVarRequirement:
        envDef:
          PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          PYTHONPATH: /app
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: ghcr.io/eoap/mastering-app-package/otsu@sha256:0541948f46a7a1a9f30f17973b7833482660f085700ccc98bb743a35a37dabae
    baseCommand: ["python", "-m", "app"]
    arguments: []
    inputs:
      raster:
        type: File
        inputBinding:
          position: 1
    outputs:
      binary_mask_item:
        outputBinding:
          glob: '*.tif'
        type: File
  - class: CommandLineTool
    id: stac
    requirements:
      InlineJavascriptRequirement: {}
      EnvVarRequirement:
        envDef:
          PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          PYTHONPATH: /app
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: ghcr.io/eoap/mastering-app-package/stac@sha256:e2ee1914cd06a0abc369034a8c8ef9ecf9b8e872b2efbc864d41c741e9faa392
    baseCommand: ["python", "-m", "app"]
    arguments: []
    inputs:
      item:
        type:
          type: array
          items: string
          inputBinding:
            prefix: --input-item
      rasters:
        type:
          type: array
          items: File
          inputBinding:
            prefix: --water-body
    outputs:
      temp_stac_catalog:
        label: temporary STAC catalog with COG outputs
        outputBinding:
          glob: .
        type: Directory
  - class: CommandLineTool
    id: stac-zarr
    requirements:
      InlineJavascriptRequirement: {}
      EnvVarRequirement:
        envDef:
          PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
          PYTHONPATH: /app
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: docker.io/library/zarr 
    baseCommand: ["python", "-m", "app"]
    arguments: []
    inputs:
      stac_catalog:
        type: Directory
        inputBinding:
          prefix: --stac-catalog
    outputs:
      zarr_stac_catalog:
        outputBinding:
          glob: .
        type: Directory
s:codeRepository:
  URL: https://github.com/eoap/zarr-cloud-native-format.git 
s:author:
  - class: s:Person
    s.name: Jane Doe
    s.email: jane.doe@acme.earth
    s.affiliation: ACME
