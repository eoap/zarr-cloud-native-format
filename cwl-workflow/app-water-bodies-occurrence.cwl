cwlVersion: v1.2
$namespaces:
  s: https://schema.org/
s:softwareVersion: 2.0.0
s:name: Water occurrence consumer workflow
s:description: Derive water occurrence from a producer GeoZarr STAC collection.
s:dateCreated: '2026-03-19'
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
  label: Water occurrence
  doc: Derive water occurrence from a producer GeoZarr STAC collection.
  inputs:
    zarr-stac-catalog:
      type: Directory
      label: GeoZarr STAC catalog
      doc: Producer collection-mode catalog with a measurements asset.
  outputs:
    stac-catalog:
      type: Directory
      outputSource: occurrence/stac-catalog
      label: Occurrence catalog
      doc: STAC catalog containing the mean water-occurrence raster.
  steps:
    occurrence:
      run: '#occurrence'
      in:
        stac_catalog: zarr-stac-catalog
      out:
      - stac-catalog
- class: CommandLineTool
  id: occurrence
  label: Compute water occurrence
  doc: Average the water-body mask over the time dimension and write a georeferenced
    raster and STAC catalog.
  requirements:
    DockerRequirement:
      dockerPull: occurrence:latest
    ResourceRequirement:
      ramMin: 2048
      ramMax: 2048
      coresMin: 1
      coresMax: 1
  baseCommand: occurrence
  inputs:
    stac_catalog:
      type: Directory
      label: Input STAC catalog
      doc: Collection-mode GeoZarr producer output.
      inputBinding:
        prefix: --stac-catalog
  outputs:
    stac-catalog:
      type: Directory
      label: Output STAC catalog
      doc: Occurrence raster and STAC metadata.
      outputBinding:
        glob: .
