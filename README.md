APIKit Python SDK
=================================================

Very simple SDK library to facilitate interacting with APIKit APIs.

# Requirements

Python 3.13+

# Usage

> Sync version

```python
import os
from apikit import APIKit

api: APIKit = APIKit('https://my-url.com')
api.authenticate(os.environ['APIKIT_APP_KEY'])
response: APIKit.Response = api.request('/my-app/my-command')

```

> Async version

```python
import os
from apikit import APIKitAsync

api: APIKit = APIKitAsync('https://my-url.com')
await api.authenticate(os.environ['APIKIT_APP_KEY'])
response: APIKit.Response = await api.request('/my-app/my-command')
```
