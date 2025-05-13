import pytest
from unittest import mock
from awx.main.credential_plugins import hashivault, azure_kv

from azure.keyvault.secrets import (
    KeyVaultSecret,
    SecretClient,
    SecretProperties,
)


def test_imported_azure_cloud_sdk_vars():
    from awx.main.credential_plugins import azure_kv

    assert len(azure_kv.clouds) > 0
    assert all([hasattr(c, 'name') for c in azure_kv.clouds])
    assert all([hasattr(c, 'suffixes') for c in azure_kv.clouds])
    assert all([hasattr(c.suffixes, 'keyvault_dns') for c in azure_kv.clouds])


def test_hashivault_approle_auth():
    kwargs = {
        'role_id': 'the_role_id',
        'secret_id': 'the_secret_id',
    }
    expected_res = {
        'role_id': 'the_role_id',
        'secret_id': 'the_secret_id',
    }
    res = hashivault.approle_auth(**kwargs)
    assert res == expected_res


def test_hashivault_kubernetes_auth():
    kwargs = {
        'kubernetes_role': 'the_kubernetes_role',
    }
    expected_res = {
        'role': 'the_kubernetes_role',
        'jwt': 'the_jwt',
    }
    with mock.patch('pathlib.Path') as path_mock:
        mock.mock_open(path_mock.return_value.open, read_data='the_jwt')
        res = hashivault.kubernetes_auth(**kwargs)
        path_mock.assert_called_with('/var/run/secrets/kubernetes.io/serviceaccount/token')
        assert res == expected_res


def test_hashivault_client_cert_auth_explicit_role():
    kwargs = {
        'client_cert_role': 'test-cert-1',
    }
    expected_res = {
        'name': 'test-cert-1',
    }
    res = hashivault.client_cert_auth(**kwargs)
    assert res == expected_res


def test_hashivault_client_cert_auth_no_role():
    kwargs = {}
    expected_res = {
        'name': None,
    }
    res = hashivault.client_cert_auth(**kwargs)
    assert res == expected_res


def test_hashivault_userpass_auth():
    kwargs = {'username': 'the_username', 'password': 'the_password'}
    expected_res = {'username': 'the_username', 'password': 'the_password'}
    res = hashivault.userpass_auth(**kwargs)
    assert res == expected_res


def test_hashivault_handle_auth_token():
    kwargs = {
        'token': 'the_token',
    }
    token = hashivault.handle_auth(**kwargs)
    assert token == kwargs['token']


def test_hashivault_handle_auth_approle():
    kwargs = {
        'role_id': 'the_role_id',
        'secret_id': 'the_secret_id',
    }
    with mock.patch.object(hashivault, 'method_auth') as method_mock:
        method_mock.return_value = 'the_token'
        token = hashivault.handle_auth(**kwargs)
        method_mock.assert_called_with(**kwargs, auth_param=kwargs)
        assert token == 'the_token'


def test_hashivault_handle_auth_kubernetes():
    kwargs = {
        'kubernetes_role': 'the_kubernetes_role',
    }
    with mock.patch.object(hashivault, 'method_auth') as method_mock:
        with mock.patch('pathlib.Path') as path_mock:
            mock.mock_open(path_mock.return_value.open, read_data='the_jwt')
            method_mock.return_value = 'the_token'
            token = hashivault.handle_auth(**kwargs)
            method_mock.assert_called_with(**kwargs, auth_param={'role': 'the_kubernetes_role', 'jwt': 'the_jwt'})
            assert token == 'the_token'


def test_hashivault_handle_auth_client_cert():
    kwargs = {
        'client_cert_public': "foo",
        'client_cert_private': "bar",
        'client_cert_role': 'test-cert-1',
    }
    auth_params = {
        'name': 'test-cert-1',
    }
    with mock.patch.object(hashivault, 'method_auth') as method_mock:
        method_mock.return_value = 'the_token'
        token = hashivault.handle_auth(**kwargs)
        method_mock.assert_called_with(**kwargs, auth_param=auth_params)
        assert token == 'the_token'


def test_hashivault_handle_auth_not_enough_args():
    with pytest.raises(Exception):
        hashivault.handle_auth()


class TestDelineaImports:
    """
    These module have a try-except for ImportError which will allow using the older library
    but we do not want the awx_devel image to have the older library,
    so these tests are designed to fail if these wind up using the fallback import
    """

    def test_dsv_import(self):
        from awx.main.credential_plugins.dsv import SecretsVault  # noqa

        # assert this module as opposed to older thycotic.secrets.vault
        assert SecretsVault.__module__ == 'delinea.secrets.vault'

    def test_tss_import(self):
        from awx.main.credential_plugins.tss import DomainPasswordGrantAuthorizer, PasswordGrantAuthorizer, SecretServer, ServerSecret  # noqa

        for cls in (DomainPasswordGrantAuthorizer, PasswordGrantAuthorizer, SecretServer, ServerSecret):
            # assert this module as opposed to older thycotic.secrets.server
            assert cls.__module__ == 'delinea.secrets.server'


class _FakeSecretClient(SecretClient):
    def get_secret(
        self: '_FakeSecretClient',
        name: str,
        version: str | None = None,
        **kwargs: str,
    ) -> KeyVaultSecret:
        props = SecretProperties(None, None)
        return KeyVaultSecret(properties=props, value='test-secret')


def test_azure_kv_invalid_env() -> None:
    """Test running outside of Azure raises error."""
    error_msg = (
        'You are not operating on an Azure VM, so the Managed Identity '
        'feature is unavailable. Please provide the full Client ID, '
        'Client Secret, and Tenant ID or run the software on an Azure VM.'
    )

    with pytest.raises(
        RuntimeError,
        match=error_msg,
    ):
        azure_kv.azure_keyvault_backend(
            url='https://test.vault.azure.net',
            client='',
            secret='client-secret',
            tenant='tenant-id',
            secret_field='secret',
            secret_version='',
        )


@pytest.mark.parametrize(
    ('client', 'secret', 'tenant'),
    (
        pytest.param('', '', '', id='managed-identity'),
        pytest.param(
            'client-id',
            'client-secret',
            'tenant-id',
            id='client-secret-credential',
        ),
    ),
)
def test_azure_kv_valid_auth(
    monkeypatch: pytest.MonkeyPatch,
    client: str,
    secret: str,
    tenant: str,
) -> None:
    """Test successful Azure authentication via Managed Identity and credentials."""
    monkeypatch.setattr(
        azure_kv,
        'SecretClient',
        _FakeSecretClient,
    )

    keyvault_secret = azure_kv.azure_keyvault_backend(
        url='https://test.vault.azure.net',
        client=client,
        secret=secret,
        tenant=tenant,
        secret_field='secret',
        secret_version='',
    )
    assert keyvault_secret == 'test-secret'
