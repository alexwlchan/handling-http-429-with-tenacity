#!/usr/bin/env python
# -*- encoding: utf-8

import urllib.error
import urllib.request

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed
from tenacity.wait import wait_base


class retry_if_http_429_error(retry_if_exception):
    """Retry strategy that retries if the exception is an ``HTTPError`` with
    a 429 status code.

    """

    def __init__(self):
        def is_http_429_error(exception):
            return (
                isinstance(exception, urllib.error.HTTPError) and
                exception.getcode() == 429
            )

        super().__init__(predicate=is_http_429_error)


class wait_for_retry_after_header(wait_base):
    """Wait strategy that tries to wait for the length specified by
    the Retry-After header, or the underlying wait strategy if not.
    See RFC 6585 § 4.

    Otherwise, wait according to the fallback strategy.
    """
    def __init__(self, fallback):
        self.fallback = fallback

    def __call__(self, retry_state):
        # retry_state is an instance of tenacity.RetryCallState.  The .outcome
        # property is the result/exception that came from the underlying function.
        exc = retry_state.outcome.exception()
        if isinstance(exc, urllib.error.HTTPError):
            retry_after = exc.headers.get("Retry-After")

            try:
                return int(retry_after)
            except (TypeError, ValueError):
                pass

        return self.fallback(retry_state)


@retry(
    retry=retry_if_http_429_error(),
    wait=wait_for_retry_after_header(fallback=wait_fixed(1)),
    stop=stop_after_attempt(3)
)
def get_url(url):
    return urllib.request.urlopen(url)


if __name__ == "__main__":
    get_url(url="https://httpbin.org/status/429")
