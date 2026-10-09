from gov_erp.observability import redact_request


def test_legacy_and_current_http_url_attributes_are_redacted():
    class Span:
        def __init__(self):
            self.attributes = {
                "http.url": "http://local/api/assistant?secret=CANARY",
                "url.full": "CANARY",
            }

        def is_recording(self):
            return True

        def set_attribute(self, key, value):
            self.attributes[key] = value

    span = Span()
    redact_request(span, {"path": "/api/assistant", "query_string": b"secret=CANARY"})
    assert "CANARY" not in str(span.attributes)
    assert span.attributes["http.url"] == "/api/assistant"
