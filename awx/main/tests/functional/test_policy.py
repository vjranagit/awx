import json
import re
from unittest import mock

import pytest
import requests.exceptions
from django.test import override_settings

from awx.main.models import Job, Inventory, Project, Organization
from awx.main.exceptions import PolicyEvaluationError
from awx.main.tasks import policy
from awx.main.tasks.policy import JobSerializer


@pytest.fixture(autouse=True)
def enable_flag():
    with override_settings(
        OPA_HOST='opa.example.com',
        FLAGS={"FEATURE_POLICY_AS_CODE_ENABLED": [("boolean", True)]},
        FLAG_SOURCES=('flags.sources.SettingsFlagsSource',),
    ):
        yield


@pytest.fixture
def opa_client():
    cls_mock = mock.MagicMock(name='OpaClient')
    instance_mock = cls_mock.return_value
    instance_mock.__enter__.return_value = instance_mock

    with mock.patch('awx.main.tasks.policy.OpaClient', cls_mock):
        yield instance_mock


@pytest.fixture
def job():
    project: Project = Project.objects.create(name='proj1', scm_type='git', scm_branch='main', scm_url='https://git.example.com/proj1')
    inventory: Inventory = Inventory.objects.create(name='inv1')
    job: Job = Job.objects.create(name='job1', extra_vars="{}", inventory=inventory, project=project)
    return job


@pytest.mark.django_db
def test_job_serializer():
    org: Organization = Organization.objects.create(name='org1')
    project: Project = Project.objects.create(name='proj1', scm_type='git', scm_branch='main', scm_url='https://git.example.com/proj1')
    inventory: Inventory = Inventory.objects.create(name='inv1')
    extra_vars = {"FOO": "value1", "BAR": "value2"}
    job: Job = Job.objects.create(name='job1', extra_vars=json.dumps(extra_vars), inventory=inventory, project=project, organization=org)

    serializer = JobSerializer(instance=job)

    assert serializer.data == {
        'id': job.id,
        'name': 'job1',
        'created': job.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        'created_by': None,
        'execution_environment': None,
        'extra_vars': extra_vars,
        'forks': 0,
        'hosts_count': 0,
        'instance_group': None,
        'inventory': inventory.id,
        'job_template': None,
        'job_type': 'run',
        'job_type_name': 'job',
        'launch_type': 'manual',
        'limit': '',
        'launched_by': {},
        'organization': {
            'id': org.id,
            'name': 'org1',
        },
        'playbook': '',
        'project': {
            'id': project.id,
            'name': 'proj1',
            'status': 'pending',
            'scm_type': 'git',
            'scm_url': 'https://git.example.com/proj1',
            'scm_branch': 'main',
            'scm_refspec': '',
            'scm_clean': False,
            'scm_track_submodules': False,
            'scm_delete_on_update': False,
        },
        'scm_branch': '',
        'scm_revision': '',
        'workflow_job_id': None,
        'workflow_node_id': None,
        'workflow_job_template': None,
    }


@pytest.mark.django_db
def test_evaluate_policy(opa_client):
    project: Project = Project.objects.create(name='proj1', scm_type='git', scm_branch='main', scm_url='https://git.example.com/proj1')
    inventory: Inventory = Inventory.objects.create(name='inv1')
    job: Job = Job.objects.create(name='job1', extra_vars="{}", inventory=inventory, project=project)

    response = {
        "result": {
            "allowed": True,
            "violations": [],
        }
    }
    opa_client.query_rule.return_value = response
    try:
        policy.evaluate_policy(job)
    except PolicyEvaluationError as e:
        pytest.fail(f"Must not raise PolicyEvaluationError: {e}")

    opa_client.query_rule.assert_called_once_with(input_data=mock.ANY, package_path='job_template', rule_name='response')


@pytest.mark.django_db
def test_evaluate_policy_allowed(opa_client, job):
    response = {
        "result": {
            "allowed": True,
            "violations": [],
        }
    }
    opa_client.query_rule.return_value = response
    try:
        policy.evaluate_policy(job)
    except PolicyEvaluationError as e:
        pytest.fail(f"Must not raise PolicyEvaluationError: {e}")

    opa_client.query_rule.assert_called_once()


@pytest.mark.django_db
def test_evaluate_policy_not_allowed(opa_client, job):
    response = {
        "result": {
            "allowed": False,
            "violations": ["Access not allowed."],
        }
    }
    opa_client.query_rule.return_value = response

    with pytest.raises(PolicyEvaluationError, match=re.escape("OPA policy denied the request, Violations: ['Access not allowed.']")):
        policy.evaluate_policy(job)

    opa_client.query_rule.assert_called_once()


@pytest.mark.django_db
def test_evaluate_policy_not_found(opa_client, job):
    response = {}
    opa_client.query_rule.return_value = response

    with pytest.raises(PolicyEvaluationError, match=re.escape('Call to OPA did not return a "result" property. The path refers to an undefined document.')):
        policy.evaluate_policy(job)

    opa_client.query_rule.assert_called_once()


@pytest.mark.django_db
def test_evaluate_policy_server_error(opa_client, job):
    http_error_msg = '500 Server Error: Internal Server Error for url: https://opa.example.com:8181/v1/data/job_template/response/invalid'
    error_response = {
        'code': 'internal_error',
        'message': (
            '1 error occurred: 1:1: rego_type_error: undefined ref: data.job_template.response.invalid\n\t'
            'data.job_template.response.invalid\n\t'
            '                           ^\n\t'
            '                           have: "invalid"\n\t'
            '                           want (one of): ["allowed" "violations"]'
        ),
    }
    response = mock.Mock()
    response.status_code = requests.codes.internal_server_error
    response.json.return_value = error_response

    opa_client.query_rule.side_effect = requests.exceptions.HTTPError(http_error_msg, response=response)

    with pytest.raises(PolicyEvaluationError, match=re.escape(f'Call to OPA failed. Code: internal_error, Message: {error_response["message"]}')):
        policy.evaluate_policy(job)

    opa_client.query_rule.assert_called_once()
