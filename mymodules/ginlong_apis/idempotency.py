import hashlib
import json
import logging

from odoo import api, SUPERUSER_ID
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY


_logger = logging.getLogger(__name__)


class _BusinessRejected(Exception):
    def __init__(self, result):
        self.result = result


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _business_key(api_code, payload):
    if api_code == "API01":
        return payload["inboundOrderNo"]
    if api_code == "API03":
        return payload["outboundOrderNo"]
    if api_code == "API05":
        return payload["countOrderNo"]
    if api_code == "API07":
        return _canonical_json([payload["owner"], payload["productCode"]])
    raise ValueError("Unsupported Ginlong idempotency API: %s" % api_code)


def execute(env, api_code, payload, operation):
    """Run the business operation and successful replay record in one request transaction."""
    business_key = _business_key(api_code, payload)
    fingerprint = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    model = env["ginlong.api.idempotency"].sudo()
    domain = [
        ("api_code", "=", api_code),
        ("business_key", "=", business_key),
        ("request_fingerprint", "=", fingerprint),
    ]
    existing = model.search(domain, limit=1)
    if existing:
        if not existing.response_json:
            raise RuntimeError("Ginlong idempotency result is incomplete")
        return json.loads(existing.response_json)

    try:
        with env.cr.savepoint():
            record = model.create({
                "api_code": api_code,
                "business_key": business_key,
                "request_fingerprint": fingerprint,
                "response_json": "{}",
            })
            result = operation()
            if not isinstance(result, dict) or not result.get("success"):
                raise _BusinessRejected(result if isinstance(result, dict) else {"success": False})
            record.response_json = _canonical_json(result)
        return result
    except _BusinessRejected as rejected:
        return rejected.result
    except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        raise
    except Exception:
        # A competing transaction may have committed the exact same request.
        # Use a fresh ORM cursor because the request uses REPEATABLE READ.
        try:
            with env.registry.cursor() as cr:
                replay_env = api.Environment(cr, SUPERUSER_ID, {})
                replay = replay_env["ginlong.api.idempotency"].search(domain, limit=1)
                if replay and replay.response_json:
                    return json.loads(replay.response_json)
        except Exception:
            _logger.exception("Ginlong idempotency replay lookup failed for %s", api_code)
        raise
