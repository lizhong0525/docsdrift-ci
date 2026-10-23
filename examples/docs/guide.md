# Getting Started

Read the [API reference](api.md) first. For details see
[advanced topics](advanced.md#tuning) (this one is broken on purpose).

## Install

```bash docsdrift:run
echo "installing (shell example, needs allow_shell)"
```

## Quick example

This example is correct and stays green:

```python docsdrift:run
import json
payload = {"name": "docsdrift", "version": 1}
assert json.loads(json.dumps(payload)) == payload
print("payload round-trips fine")
```

## Drifted example

This one drifted from the codebase and now fails:

```python docsdrift:run
from docsdrift import deprecated_function  # removed in v0.2
deprecated_function()
```

A block without the marker is documentation-only and never runs:

```python
do_not_execute_this()
```
