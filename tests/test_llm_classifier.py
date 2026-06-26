"""Tests for LLMClassifier with a stubbed client.

These exercise the real parse, retry, and fallback path without a network call or an API key.
A fake client is injected in place of the OpenAI SDK client and returns canned responses, so
the JSON parsing, schema validation, single retry, and unknown fallback all run.
"""

from ai.classifier import LLMClassifier
from ai.themes import ReviewTheme


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, queue):
        self.queue = list(queue)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return _Resp(item)


class _Chat:
    def __init__(self, queue):
        self.completions = _Completions(queue)


class _StubClient:
    def __init__(self, queue):
        self.chat = _Chat(queue)


def make_clf(queue):
    # api_key is a dummy; the OpenAI constructor does not call out, and the client is replaced.
    clf = LLMClassifier(model="test-model", prompt_version="v1", api_key="dummy")
    clf._client = _StubClient(queue)
    return clf


def test_parses_a_valid_json_response():
    clf = make_clf(['{"theme": "dairy", "confidence": 0.9, "evidence": "milk was sour"}'])
    r = clf.classify("the latte tasted sour")
    assert r.theme == ReviewTheme.dairy
    assert r.confidence == 0.9
    assert clf._client.chat.completions.calls == 1


def test_retries_once_then_succeeds():
    clf = make_clf(["not json at all", '{"theme": "wifi", "confidence": 0.7, "evidence": "wifi"}'])
    r = clf.classify("the wifi never connects")
    assert r.theme == ReviewTheme.wifi
    assert clf._client.chat.completions.calls == 2


def test_falls_back_to_unknown_after_two_failures():
    clf = make_clf(["nope", "still broken"])
    r = clf.classify("some review")
    assert r.theme == ReviewTheme.unknown
    assert r.confidence == 0.0
    assert clf._client.chat.completions.calls == 2


def test_skips_the_api_call_on_empty_text():
    clf = make_clf([])  # empty queue: any create() call would raise IndexError
    r = clf.classify("   ")
    assert r.theme == ReviewTheme.unknown
    assert clf._client.chat.completions.calls == 0
