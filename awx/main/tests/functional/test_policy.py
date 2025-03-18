import json
from unittest import mock

import pytest
import requests.exceptions
from django.test import override_settings

from awx.main.models import (
    Job,
    Inventory,
    Project,
    Organization,
    JobTemplate,
    Credential,
    CredentialType,
    User,
    Team,
    Label,
    WorkflowJob,
    WorkflowJobNode,
    InventorySource,
)
from awx.main.exceptions import PolicyEvaluationError
from awx.main.tasks import policy
from awx.main.tasks.policy import JobSerializer


def _parse_exception_message(exception: PolicyEvaluationError):
    pe_plain = str(exception.value)

    assert "This job cannot be executed due to a policy violation or error. See the following details:" in pe_plain

    violation_message = "This job cannot be executed due to a policy violation or error. See the following details:"
    return eval(pe_plain.split(violation_message)[1].strip())


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
    inventory: Inventory = Inventory.objects.create(name='inv1', opa_query_path="inventory/response")
    org: Organization = Organization.objects.create(name="org1", opa_query_path="organization/response")
    jt: JobTemplate = JobTemplate.objects.create(name="jt1", opa_query_path="job_template/response")
    job: Job = Job.objects.create(name='job1', extra_vars="{}", inventory=inventory, project=project, organization=org, job_template=jt)
    return job


@pytest.mark.django_db
def test_job_serializer():
    user: User = User.objects.create(username='user1')
    org: Organization = Organization.objects.create(name='org1')

    team: Team = Team.objects.create(name='team1', organization=org)
    team.admin_role.members.add(user)

    project: Project = Project.objects.create(name='proj1', scm_type='git', scm_branch='main', scm_url='https://git.example.com/proj1')
    inventory: Inventory = Inventory.objects.create(name='inv1', description='Demo inventory')
    inventory_source: InventorySource = InventorySource.objects.create(name='inv-src1', source='file', inventory=inventory)
    extra_vars = {"FOO": "value1", "BAR": "value2"}

    CredentialType.setup_tower_managed_defaults()
    cred_type_ssh: CredentialType = CredentialType.objects.get(kind='ssh')
    cred: Credential = Credential.objects.create(name="cred1", description='Demo credential', credential_type=cred_type_ssh, organization=org)

    label: Label = Label.objects.create(name='label1', organization=org)

    job: Job = Job.objects.create(
        name='job1', extra_vars=json.dumps(extra_vars), inventory=inventory, project=project, organization=org, created_by=user, launch_type='workflow'
    )
    # job.unified_job_node.workflow_job = workflow_job
    job.credentials.add(cred)
    job.labels.add(label)

    workflow_job: WorkflowJob = WorkflowJob.objects.create(name='wf-job1')
    WorkflowJobNode.objects.create(job=job, workflow_job=workflow_job)

    serializer = JobSerializer(instance=job)

    assert serializer.data == {
        'id': job.id,
        'name': 'job1',
        'created': job.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        'created_by': {
            'id': user.id,
            'username': 'user1',
            'is_superuser': False,
            'teams': [
                {'id': team.id, 'name': 'team1'},
            ],
        },
        'credentials': [
            {
                'id': cred.id,
                'name': 'cred1',
                'description': 'Demo credential',
                'organization': {
                    'id': org.id,
                    'name': 'org1',
                },
                'credential_type': cred_type_ssh.id,
                'kind': 'ssh',
                'managed': False,
                'kubernetes': False,
                'cloud': False,
            },
        ],
        'execution_environment': None,
        'extra_vars': extra_vars,
        'forks': 0,
        'hosts_count': 0,
        'instance_group': None,
        'inventory': {
            'id': inventory.id,
            'name': 'inv1',
            'description': 'Demo inventory',
            'kind': '',
            'total_hosts': 0,
            'total_groups': 0,
            'has_inventory_sources': False,
            'total_inventory_sources': 0,
            'has_active_failures': False,
            'hosts_with_active_failures': 0,
            'inventory_sources': [
                {
                    'id': inventory_source.id,
                    'name': 'inv-src1',
                    'source': 'file',
                    'status': 'never updated',
                }
            ],
        },
        'job_template': None,
        'job_type': 'run',
        'job_type_name': 'job',
        'labels': [
            {
                'id': label.id,
                'name': 'label1',
                'organization': {
                    'id': org.id,
                    'name': 'org1',
                },
            },
        ],
        'launch_type': 'workflow',
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
        'workflow_job': {
            'id': workflow_job.id,
            'name': 'wf-job1',
        },
        'workflow_job_template': None,
    }


@pytest.mark.django_db
def test_evaluate_policy_missing_opa_query_path_field(opa_client):
    project: Project = Project.objects.create(name='proj1', scm_type='git', scm_branch='main', scm_url='https://git.example.com/proj1')
    inventory: Inventory = Inventory.objects.create(name='inv1')
    org: Organization = Organization.objects.create(name="org1")
    jt: JobTemplate = JobTemplate.objects.create(name="jt1")
    job: Job = Job.objects.create(name='job1', extra_vars="{}", inventory=inventory, project=project, organization=org, job_template=jt)

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

    assert opa_client.query_rule.call_count == 0


@pytest.mark.django_db
def test_evaluate_policy(opa_client, job):
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

    opa_client.query_rule.assert_has_calls(
        [
            mock.call(input_data=mock.ANY, package_path='organization/response'),
            mock.call(input_data=mock.ANY, package_path='inventory/response'),
            mock.call(input_data=mock.ANY, package_path='job_template/response'),
        ],
        any_order=False,
    )
    assert opa_client.query_rule.call_count == 3


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

    assert opa_client.query_rule.call_count == 3


@pytest.mark.django_db
def test_evaluate_policy_not_allowed(opa_client, job):
    response = {
        "result": {
            "allowed": False,
            "violations": ["Access not allowed."],
        }
    }
    opa_client.query_rule.return_value = response

    with pytest.raises(PolicyEvaluationError) as pe:
        policy.evaluate_policy(job)

    pe_plain = str(pe.value)
    assert "Errors:" not in pe_plain

    exception = _parse_exception_message(pe)

    assert exception["Violations"]["Organization"] == ["Access not allowed."]
    assert exception["Violations"]["Inventory"] == ["Access not allowed."]
    assert exception["Violations"]["Job template"] == ["Access not allowed."]

    assert opa_client.query_rule.call_count == 3


@pytest.mark.django_db
def test_evaluate_policy_not_found(opa_client, job):
    response = {}
    opa_client.query_rule.return_value = response

    with pytest.raises(PolicyEvaluationError) as pe:
        policy.evaluate_policy(job)

    missing_result_property = 'Call to OPA did not return a "result" property. The path refers to an undefined document.'

    exception = _parse_exception_message(pe)
    assert exception["Errors"]["Organization"] == missing_result_property
    assert exception["Errors"]["Inventory"] == missing_result_property
    assert exception["Errors"]["Job template"] == missing_result_property

    assert opa_client.query_rule.call_count == 3


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

    with pytest.raises(PolicyEvaluationError) as pe:
        policy.evaluate_policy(job)

    exception = _parse_exception_message(pe)
    assert exception["Errors"]["Organization"] == f'Call to OPA failed. Code: internal_error, Message: {error_response["message"]}'
    assert exception["Errors"]["Inventory"] == f'Call to OPA failed. Code: internal_error, Message: {error_response["message"]}'
    assert exception["Errors"]["Job template"] == f'Call to OPA failed. Code: internal_error, Message: {error_response["message"]}'

    assert opa_client.query_rule.call_count == 3


@pytest.mark.django_db
def test_evaluate_policy_invalid_result(opa_client, job):
    response = {
        "result": {
            "absolutely": "no!",
        }
    }
    opa_client.query_rule.return_value = response

    with pytest.raises(PolicyEvaluationError) as pe:
        policy.evaluate_policy(job)

    invalid_result = 'OPA policy returned invalid result.'

    exception = _parse_exception_message(pe)
    assert exception["Errors"]["Organization"] == invalid_result
    assert exception["Errors"]["Inventory"] == invalid_result
    assert exception["Errors"]["Job template"] == invalid_result

    assert opa_client.query_rule.call_count == 3


@pytest.mark.django_db
def test_evaluate_policy_failed_exception(opa_client, job):
    error_response = {}
    response = mock.Mock()
    response.status_code = requests.codes.internal_server_error
    response.json.return_value = error_response

    opa_client.query_rule.side_effect = ValueError("Invalid JSON")

    with pytest.raises(PolicyEvaluationError) as pe:
        policy.evaluate_policy(job)

    opa_failed_exception = 'Call to OPA failed. Exception: Invalid JSON'

    exception = _parse_exception_message(pe)
    assert exception["Errors"]["Organization"] == opa_failed_exception
    assert exception["Errors"]["Inventory"] == opa_failed_exception
    assert exception["Errors"]["Job template"] == opa_failed_exception

    assert opa_client.query_rule.call_count == 3
