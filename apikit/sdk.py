import asyncio
import os
import typing
import time

import httpx
import orjson as json
import ormsgpack as msgpack


class APIKitException(Exception):
    pass


JSONPrimitive: typing.TypeAlias = typing.Union[str, int, float, bool, None]
JSON: typing.TypeAlias = typing.Union[
    JSONPrimitive,
    # JSON arrays are ordered and indexable
    typing.Sequence["JSON"],  # list, tuple
    # Mutable mappings
    dict[str, "JSON"],  # dict with string keys
]


class Response(typing.TypedDict, total=False):
    status_code: int
    is_success: bool
    # Success fields
    data: JSON
    # Error fields
    text: str
    summary: str
    content: bytes


class APIKit:
    Response: typing.ClassVar[typing.TypeAlias] = Response
    JSON: typing.ClassVar[typing.TypeAlias] = JSON

    def __init__(self, url: str) -> None:
        self.url = url

    def authenticate(self, access_token: str) -> None:
        pass

    def request(
        self,
        path: str,
        *,
        method: str = "POST",
        params: dict[str, JSON] | None = None,  # For JSON
        headers: dict[str, JSON] | None = None,
        use_msgpack: bool = False,  # For MsgPack
        input_form_encoded: bool = False,  # For HTML-Form input
        output_json: bool = True,  # auto convert json string to object (json.loads)
        output_binary: bool = False,  # read response.content instead of response.text
        timeout: int | None = None,
        retries: int = 0,
        delay_secs: int = 2,
        debug: bool = True,
    ) -> Response:
        """
        Usage:
        response: Response = apikit.request(path, params, headers)
        if response['is_success']:
            response['data']
        else:
            response['status_code'], response['error'], response['text']
        """

        timeout = timeout or int(os.getenv("APIKIT_REQUEST_TIMEOUT_SECS", "5"))
        r: httpx.Response
        with httpx.Client(verify=True, follow_redirects=True, http2=True) as client:
            try:
                # https://www.python-httpx.org/api/
                if method == "GET":
                    if params:
                        r = client.request(
                            method,
                            path,
                            params={k: str(v) for k, v in params.items()}
                            if params
                            else None,  # GET
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    else:
                        # Some APIs like GitHub's doesn't support sending GET with params
                        r = client.request(
                            method,
                            path,
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                else:
                    if use_msgpack:
                        headers = headers or {}
                        headers["Content-Type"] = "application/msgpack"
                        r = client.request(
                            method,
                            path,
                            content=msgpack.packb(params),  # MsgPack bytes
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    elif input_form_encoded:  # For HTML-Form input
                        r = client.request(
                            method,
                            path,
                            data=params,  # POST
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    else:  # JSON
                        r = client.request(
                            method,
                            path,
                            # Using json=, similar to JSON.stringify. Otherwise it will be converted as form-encoded params.
                            json=params,  # POST
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )

                params_str: str
                headers_str: str
                if r.status_code >= 400:
                    params_str = (
                        " ".join(f"{k}:={json.dumps(v)}" for k, v in params.items())
                        if params
                        else ""
                    )
                    headers_str = (
                        " ".join(f"{k}:?" for k, v in headers.items())
                        if headers
                        else ""
                    )
                    # Only for debug in development env, because it will expose keys to log systems
                    print(
                        f"http --follow --verify=no {method} {path} {params_str} {headers_str}",
                    )
                    print(f"> {r.status_code} {r.text}")
                elif debug:
                    params_str = (
                        " ".join(f"{k}:={json.dumps(v)}" for k, v in params.items())
                        if params
                        else ""
                    )
                    headers_str = (
                        " ".join(f"{k}:{v!r}" for k, v in headers.items())
                        if headers
                        else ""
                    )
                    # Only for debug in development env, because it will expose keys to log systems
                    print(
                        f"http --follow --verify=no {method} {path} {params_str} {headers_str}",
                    )
                    print(f"> {r.status_code} {r.text}")

                is_success: bool = bool(r.status_code >= 200 and r.status_code <= 299)
                if (not is_success) and retries > 0:
                    time.sleep(delay_secs)
                    return self.request(
                        path=path,
                        params=params,
                        headers=headers,
                        method=method,
                        input_form_encoded=input_form_encoded,
                        output_json=output_json,
                        timeout=timeout,
                        debug=debug,
                        retries=retries - 1,
                        delay_secs=delay_secs,
                    )

                if output_binary:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        "content": r.content,
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }
                elif output_json:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        # Traefik returns a non-json 404 page, the parse fail
                        # It may return a dict, list, int, float, bool, string: JSON
                        # r.content can be empty, specially for 202, 204 results
                        "data": json.loads(r.content) if r.content else {},  # orjson
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }
                else:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        # Traefik returns a non-json 404 page, the parse fail
                        "text": r.text,
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }
            except (
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.HTTPError,
                httpx.DecodingError,
                UnicodeDecodeError,
            ) as e:
                if retries > 0:
                    time.sleep(delay_secs)
                    return self.request(
                        path=path,
                        params=params,
                        headers=headers,
                        method=method,
                        input_form_encoded=input_form_encoded,
                        output_json=output_json,
                        timeout=timeout,
                        debug=debug,
                        retries=retries - 1,
                        delay_secs=delay_secs,
                    )
                return log_exception(method, path, r, e, timeout)


class APIKitAsync:
    def __init__(self, url: str) -> None:
        self.url = url

    async def authenticate(self, access_token: str) -> None:
        pass

    async def request(
        self,
        path: str,
        *,
        method: str = "POST",
        params: dict[str, JSON] | None = None,  # For JSON
        headers: dict[str, JSON] | None = None,
        use_msgpack: bool = False,  # For MsgPack
        input_form_encoded: bool = False,  # For HTML-Form input
        output_json: bool = True,  # auto convert json string to object (json.loads)
        output_binary: bool = False,  # read response.content instead of response.text
        timeout: int | None = None,
        retries: int = 0,
        delay_secs: int = 2,
        debug: bool = True,
    ) -> Response:
        """
        Usage:
        response: Response = await apikit.request(path, params=params, headers=headers)
        if response['is_success']:
            response['data']
        else:
            response['status_code'], response['error'], response['text']
        """

        timeout = timeout or int(os.getenv("APIKIT_REQUEST_TIMEOUT_SECS", "5"))
        r: httpx.Response
        async with httpx.AsyncClient(
            verify=True, follow_redirects=True, http2=True
        ) as client:
            try:
                # https://www.python-httpx.org/api/
                if method == "GET":
                    if params:
                        r = await client.request(
                            method,
                            path,
                            params={k: str(v) for k, v in params.items()}
                            if params
                            else None,  # GET
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    else:
                        # Some APIs like GitHub's doesn't support sending GET with params
                        r = await client.request(
                            method,
                            path,
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                else:
                    if use_msgpack:
                        headers = headers or {}
                        headers["Content-Type"] = "application/msgpack"
                        r = await client.request(
                            method,
                            path,
                            content=msgpack.packb(params),  # MsgPack bytes
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    elif input_form_encoded:  # For HTML-Form input
                        r = await client.request(
                            method,
                            path,
                            data=params,  # POST
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )
                    else:  # JSON
                        r = await client.request(
                            method,
                            path,
                            # Using json=, similar to JSON.stringify. Otherwise it will be converted as form-encoded params.
                            json=params,  # POST
                            headers={k: str(v) for k, v in headers.items()}
                            if headers
                            else None,
                            timeout=timeout,
                        )

                params_str: str
                headers_str: str
                if r.status_code >= 400:
                    params_str = (
                        " ".join(f"{k}:={json.dumps(v)}" for k, v in params.items())
                        if params
                        else ""
                    )
                    headers_str = (
                        " ".join(f"{k}:?" for k, v in headers.items())
                        if headers
                        else ""
                    )
                    # Only for debug in development env, because it will expose keys to log systems
                    print(
                        f"http --follow --verify=no {method} {path} {params_str} {headers_str}",
                    )
                    print(f"> {r.status_code} {r.text}")
                elif debug:
                    params_str = (
                        " ".join(f"{k}:={json.dumps(v)}" for k, v in params.items())
                        if params
                        else ""
                    )
                    headers_str = (
                        " ".join(f"{k}:{v!r}" for k, v in headers.items())
                        if headers
                        else ""
                    )
                    # Only for debug in development env, because it will expose keys to log systems
                    print(
                        f"http --follow --verify=no {method} {path} {params_str} {headers_str}",
                    )
                    print(f"> {r.status_code} {r.text}")

                is_success: bool = bool(r.status_code >= 200 and r.status_code <= 299)
                if (not is_success) and retries > 0:
                    await asyncio.sleep(delay_secs)
                    return await self.request(
                        path=path,
                        params=params,
                        headers=headers,
                        method=method,
                        input_form_encoded=input_form_encoded,
                        output_json=output_json,
                        timeout=timeout,
                        debug=debug,
                        retries=retries - 1,
                        delay_secs=delay_secs,
                    )

                if output_binary:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        "content": r.content,
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }
                elif output_json:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        # Traefik returns a non-json 404 page, the parse fail
                        # It may return a dict, list, int, float, bool, string: JSON
                        # r.content can be empty, specially for 202, 204 results
                        "data": json.loads(r.content) if r.content else {},  # orjson
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }
                else:
                    return {
                        "status_code": r.status_code,
                        "is_success": is_success,
                        # Returning as result as bytes.
                        # Traefik returns a non-json 404 page, the parse fail
                        "text": r.text,
                        "summary": f"{r.status_code} {'success' if is_success else 'fail: ' + r.text}",
                    }

            except Exception as e:
                if retries > 0:
                    await asyncio.sleep(delay_secs)
                    return await self.request(
                        path=path,
                        params=params,
                        headers=headers,
                        method=method,
                        input_form_encoded=input_form_encoded,
                        output_json=output_json,
                        timeout=timeout,
                        debug=debug,
                        retries=retries - 1,
                        delay_secs=delay_secs,
                    )
                return log_exception(method, path, r, e, timeout)


def log_exception(
    method: str, path: str, r: httpx.Response, e: Exception, timeout: int
) -> Response:
    if isinstance(e, httpx.ConnectError):
        print(
            f"http --follow --verify=no {method} {path} > {e!s}",
        )
        return {
            "is_success": False,
            "status_code": -3,
            "summary": f"Connection error: {type(e)} {e} {path}",
        }
    elif isinstance(e, httpx.HTTPError):
        print(
            f"http --follow --verify=no {method} {path} > {e!s}",
        )
        # All connection attempts failed: DNS not found
        # Name does not resolve: Wrong DNS
        return {
            "is_success": False,
            "status_code": -4,
            "summary": f"{type(e)}: {e!s}",
        }
    if isinstance(e, (httpx.ConnectTimeout, httpx.ReadTimeout)):
        print(
            f"http --follow --verify=no {method} {path} > [timeout {timeout}s] {e!s}",
        )
        return {
            "is_success": False,
            "status_code": -5,
            "summary": f"Timeout ({timeout}s) for {path}",
        }
    elif isinstance(e, (httpx.DecodingError, UnicodeDecodeError)):
        print(
            f"http --follow --verify=no {method} {path} > {e!s}",
        )
        # Handle bad/malformed JSON
        return {
            "status_code": r.status_code,
            "is_success": False,
            "data": {},
            "text": r.text,
            "summary": f"{r.status_code} error {e!s}",
        }
