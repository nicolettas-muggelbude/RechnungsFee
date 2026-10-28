import zipfile

with zipfile.ZipFile('/tmp/kundenpruefung.rfplugin', 'w') as z:

z.write('testplugin.wasm', 'plugin.wasm')
z.writestr('plugin.toml', '''[plugin]

id = "de.test.kundenpruefung"
name = "Kundenprüfung"
version = "1.0.0"
author = "Test"
description = "Prüft Kunden vor dem Speichern."
api_version = "0.1.0"

[permissions]
  entities = [ { type = "customer", actions = ["read"] } ]
  hooks = [ "customer:create:before", "customer:update:before" ]
  ''')
