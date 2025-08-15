import pytest

from apikit.sdk import APIKit, APIKitAsync, APIKitException


def test_sync():
    apikit = APIKit("https://localhost")
    apikit.request("/status/ping")
    with pytest.raises(APIKitException, match=".*Invalid Access Token.*"):
        apikit.authenticate("")
    apikit.authenticate("sometoken")
    apikit.request("/status/ping")


async def test_async():
    apikit = APIKitAsync("https://localhost")
    await apikit.request("/status/ping")
    await apikit.authenticate("")
    await apikit.request("/status/ping")
