# Guide

This link is broken: [missing](does-not-exist.md).
This anchor is broken: [nope](api.md#no-such-section).
This one is fine: [api](api.md).

```python docsdrift:run
import sys
print("about to fail", file=sys.stderr)
sys.exit(3)
```
