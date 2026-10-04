# Demo Runbook

Use two terminals: TiTiler keeps running in foreground.

## Terminal 1 (keep open)

```bash
task cwl:run:producer:item
task titiler:eopf:run:results:item:patched TITILER_PORT=8080
```

Wait until TiTiler is up, then quick-check:

```bash
curl -fsSL "http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/dataset" | head -c 200 && echo
```

## Terminal 2

```bash
task examples:serve EXAMPLES_PORT=8090
```

Open:

`http://127.0.0.1:8090/examples/titiler-eopf-client.html`

In the client UI:

- Base URL: `http://127.0.0.1:8080`
- Collection ID: `water-bodies`
- Item ID: `water-bodies`
- Click `Load measurements and dates`
- Click `Build layers from renders`
