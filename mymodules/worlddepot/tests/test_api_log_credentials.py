import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.worlddepot.controllers import api_logs, auth_controller, validator_token


class _CursorContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        pass


class _FakeEnvironment(dict):
    def __init__(self, values):
        super().__init__(values)
        self.cr = SimpleNamespace(dbname='odooce_karlrapp')
        self.uid = 1
        self.context = {}


@tagged('post_install', '-at_install')
class TestAPILogCredentials(TransactionCase):
    def _run_logged_endpoint(self, path, request_body, response_body, fail_log=False):
        log_model = MagicMock()
        if fail_log:
            log_model.sudo.return_value.create.side_effect = RuntimeError('database unavailable')
        fake_env = MagicMock()
        fake_env.__getitem__.return_value = log_model
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=request_body.encode('utf-8'),
                remote_addr='127.0.0.1',
                path=path,
            ),
            env=SimpleNamespace(
                cr=SimpleNamespace(dbname='odooce_karlrapp'),
                uid=1,
                context={},
            ),
            registry=SimpleNamespace(cursor=lambda: _CursorContext()),
            api_user=False,
        )

        @api_logs.api_logger
        def endpoint():
            return response_body

        with patch.object(api_logs, 'request', fake_request), \
                patch.object(api_logs.api, 'Environment', return_value=fake_env):
            result = endpoint()
        return result, log_model.sudo.return_value.create, api_logs._logger.name

    def _run_auth_endpoint(self, path, request_body, fail_log=False):
        log_model = MagicMock()
        if fail_log:
            log_model.sudo.return_value.create.side_effect = RuntimeError('database unavailable')
        api_user = SimpleNamespace(
            verify_secret=Mock(return_value=True),
            user_id=SimpleNamespace(id=7),
        )
        api_user_model = MagicMock()
        api_user_model.sudo.return_value.search.return_value = api_user
        token_model = MagicMock()
        fake_env = _FakeEnvironment({
            'world.depot.api.log': log_model,
            'world.depot.api.user': api_user_model,
            'world.depot.api.token': token_model,
        })
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=request_body.encode('utf-8'),
                remote_addr='127.0.0.1',
                path=path,
            ),
            env=fake_env,
            registry=SimpleNamespace(cursor=lambda: _CursorContext()),
            api_user=False,
        )

        with patch.object(auth_controller, 'request', fake_request), \
                patch.object(api_logs, 'request', fake_request), \
                patch.object(api_logs.api, 'Environment', return_value=fake_env), \
                patch.object(auth_controller.secrets, 'token_urlsafe', return_value='issued-token-for-test'):
            result = auth_controller.AuthController().generate_token()
        return result, log_model.sudo.return_value.create

    def test_auth_request_and_response_credentials_are_masked_in_api_log_only(self):
        api_secret = 'ginlong-secret-for-test'
        access_token = 'issued-token-for-test'
        request_body = json.dumps({'api_key': 'test-key', 'api_secret': api_secret})

        result, create_log = self._run_auth_endpoint(
            '/world_depot/api/auth/getToken', request_body
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['code'], '200')
        self.assertEqual(result['data']['access_token'], access_token)
        self.assertEqual(result['data']['expires_in'], 3600)
        self.assertIn('expires_at', result['data'])
        log_values = create_log.call_args.args[0]
        serialized_log = json.dumps(log_values, ensure_ascii=False, default=str)
        self.assertNotIn(api_secret, serialized_log)
        self.assertNotIn(access_token, serialized_log)
        self.assertIn('test-key', serialized_log)
        self.assertIn('[REDACTED]', serialized_log)

    def test_malformed_auth_request_body_is_not_logged_raw(self):
        secret_fragment = 'secret-fragment-for-test'
        result, create_log = self._run_auth_endpoint(
            '/world_depot/api/auth/token',
            '{"api_secret":"' + secret_fragment,
        )

        self.assertIn('error', result)
        log_values = create_log.call_args.args[0]
        self.assertNotIn(secret_fragment, json.dumps(log_values, ensure_ascii=False, default=str))
        self.assertEqual(log_values['request_data'], '[authentication request omitted]')

    def test_auth_token_endpoint_masks_top_level_access_token(self):
        access_token = 'issued-token-for-test'
        result, create_log = self._run_auth_endpoint(
            '/world_depot/api/auth/token',
            json.dumps({'api_key': 'test-key', 'api_secret': 'top-level-secret'}),
        )

        self.assertEqual(result['access_token'], access_token)
        self.assertEqual(result['expires_in'], 3600)
        self.assertIn('expires_at', result)
        log_values = create_log.call_args.args[0]
        self.assertNotIn(access_token, json.dumps(log_values, ensure_ascii=False, default=str))
        self.assertIn('[REDACTED]', log_values['response_data'])

    def test_non_auth_api_payload_is_not_redacted(self):
        request_body = json.dumps({'remark': 'keep-business-payload'})
        response_body = {'success': True, 'data': {'reference': 'ORDER-001'}}
        result, create_log, _logger_name = self._run_logged_endpoint(
            '/world_depot/api/example', request_body, response_body
        )

        self.assertEqual(result, response_body)
        log_values = create_log.call_args.args[0]
        self.assertEqual(log_values['request_data'], request_body)
        self.assertEqual(json.loads(log_values['response_data']), response_body)

    def test_api_log_failure_fallback_does_not_print_auth_secret(self):
        api_secret = 'fallback-secret-for-test'
        request_body = json.dumps({'api_key': 'test-key', 'api_secret': api_secret})
        with self.assertLogs(api_logs._logger.name, level='DEBUG') as captured:
            result, _create_log = self._run_auth_endpoint(
                '/world_depot/api/auth/token', request_body,
                fail_log=True,
            )

        self.assertEqual(result['access_token'], 'issued-token-for-test')
        output = '\n'.join(captured.output)
        self.assertNotIn(api_secret, output)
        self.assertIn('[REDACTED]', output)

    def _run_token_validator(self, token, token_record=False):
        token_model = MagicMock()
        token_model.sudo.return_value.search.return_value = token_record
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(headers={'Authorization': 'Bearer ' + token}),
            env={
                'world.depot.api.token': token_model,
            },
        )

        @validator_token.validate_token
        def endpoint():
            return 'unexpectedly accepted'

        with patch.object(validator_token, 'request', fake_request):
            return endpoint()

    def test_invalid_token_is_not_written_to_application_log(self):
        token = 'invalid-token-for-test'
        with self.assertLogs(validator_token._logger.name, level='WARNING') as captured:
            response = self._run_token_validator(token)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.get_data(as_text=True)), {'error': 'Invalid token'})
        self.assertNotIn(token, '\n'.join(captured.output))

    def test_expired_token_is_not_written_to_application_log(self):
        token = 'expired-token-for-test'
        token_record = SimpleNamespace(expires=datetime(2000, 1, 1), unlink=Mock())
        with self.assertLogs(validator_token._logger.name, level='INFO') as captured:
            response = self._run_token_validator(token, token_record)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.get_data(as_text=True)), {'error': 'Token expired'})
        self.assertNotIn(token, '\n'.join(captured.output))
        token_record.unlink.assert_called_once_with()
