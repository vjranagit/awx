import json
import tempfile
import contextlib

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from flags.state import flag_enabled
from opa_client import OpaClient
from requests import HTTPError
from rest_framework import serializers
from rest_framework import fields

from awx.main import models
from awx.main.exceptions import PolicyEvaluationError


class _UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ('id', 'username', 'is_superuser')


class _ExecutionEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExecutionEnvironment
        fields = (
            'id',
            'name',
            'image',
            'pull',
        )


class _InstanceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InstanceGroup
        fields = (
            'id',
            'name',
            'capacity',
            'jobs_running',
            'jobs_total',
            'max_concurrent_jobs',
            'max_forks',
        )


class _InventorySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InventorySource
        fields = ('id', 'name', 'type', 'kind')


class _InventorySerializer(serializers.ModelSerializer):
    inventory_sources = _InventorySourceSerializer(many=True)

    class Meta:
        model = models.Inventory
        fields = (
            'id',
            'name',
            'description',
            'total_hosts',
            'total_groups',
            'inventory_sources',
        )


class _JobTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JobTemplate
        fields = (
            'id',
            'name',
            'job_type',
        )


class _WorkflowJobTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WorkflowJobTemplate
        fields = (
            'id',
            'name',
            'job_type',
        )


class _OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Organization
        fields = (
            'id',
            'name',
        )


class _ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Project
        fields = (
            'id',
            'name',
            'status',
            'scm_type',
            'scm_url',
            'scm_branch',
            'scm_refspec',
            'scm_clean',
            'scm_track_submodules',
            'scm_delete_on_update',
        )


class JobSerializer(serializers.ModelSerializer):
    created_by = _UserSerializer()
    execution_environment = _ExecutionEnvironmentSerializer()
    instance_group = _InstanceGroupSerializer()
    job_template = _JobTemplateSerializer()
    organization = _OrganizationSerializer()
    project = _ProjectSerializer()
    extra_vars = fields.SerializerMethodField()
    hosts_count = fields.SerializerMethodField()
    workflow_job_template = fields.SerializerMethodField()

    class Meta:
        model = models.Job
        fields = (
            'id',
            'name',
            'created',
            'created_by',
            'execution_environment',
            'extra_vars',
            'forks',
            'hosts_count',
            'instance_group',
            'inventory',
            'job_template',
            'job_type',
            'job_type_name',
            'launch_type',
            'limit',
            'launched_by',
            'organization',
            'playbook',
            'project',
            'scm_branch',
            'scm_revision',
            'workflow_job_id',
            'workflow_node_id',
            'workflow_job_template',
        )

    def get_extra_vars(self, obj: models.Job):
        return json.loads(obj.display_extra_vars())

    def get_hosts_count(self, obj: models.Job):
        return obj.hosts.count()

    def get_workflow_job_template(self, obj: models.Job):
        workflow_job: models.WorkflowJob = obj.get_workflow_job()
        if workflow_job is None:
            return None

        workflow_job_template: models.WorkflowJobTemplate = workflow_job.workflow_job_template
        if workflow_job_template is None:
            return None

        return _WorkflowJobTemplateSerializer().to_representation(workflow_job_template)


class OPAResultSerializer(serializers.Serializer):
    allowed = fields.BooleanField(required=True)
    violations = fields.ListField(child=fields.CharField())


class OPA_AUTH_TYPES:
    NONE = 'None'
    TOKEN = 'Token'
    CERTIFICATE = 'Certificate'


@contextlib.contextmanager
def opa_cert_file():
    if settings.OPA_AUTH_TYPE == OPA_AUTH_TYPES.CERTIFICATE:
        with tempfile.NamedTemporaryFile(delete=True, mode='w', suffix=".pem") as cert_temp:
            cert_temp.write(settings.OPA_AUTH_CA_CERT)
            cert_temp.write("\n")
            cert_temp.write(settings.OPA_AUTH_CLIENT_CERT)
            cert_temp.write("\n")
            cert_temp.write(settings.OPA_AUTH_CLIENT_KEY)
            cert_temp.write("\n")
            cert_temp.flush()
            yield cert_temp.name
    elif settings.OPA_SSL and settings.OPA_AUTH_CA_CERT:
        with tempfile.NamedTemporaryFile(delete=True, mode='w', suffix=".pem") as cert_temp:
            cert_temp.write(settings.OPA_AUTH_CA_CERT)
            cert_temp.write("\n")
            cert_temp.flush()
            yield cert_temp.name
    else:
        yield None


@contextlib.contextmanager
def opa_client(headers=None):
    with opa_cert_file() as cert_temp_file_name:
        with OpaClient(
            host=settings.OPA_HOST,
            port=settings.OPA_PORT,
            headers=headers,
            ssl=settings.OPA_SSL,
            cert=cert_temp_file_name,
            retries=settings.OPA_REQUEST_RETRIES,
            timeout=settings.OPA_REQUEST_TIMEOUT,
        ) as client:
            yield client


def evaluate_policy(instance):
    # Policy evaluation for Policy as Code feature
    if not flag_enabled("FEATURE_POLICY_AS_CODE_ENABLED"):
        return

    if not settings.OPA_HOST:
        return

    if not isinstance(instance, models.Job):
        return

    input_data = JobSerializer(instance=instance).data

    headers = None
    if settings.OPA_AUTH_TYPE == OPA_AUTH_TYPES.TOKEN:
        headers = {'Authorization': 'Bearer {}'.format(settings.OPA_AUTH_TOKEN)}

    if settings.OPA_AUTH_TYPE == OPA_AUTH_TYPES.CERTIFICATE and not settings.OPA_SSL:
        raise PolicyEvaluationError(_('OPA_AUTH_TYPE=Certificate requires OPA_SSL to be enabled.'))

    cert_settings_missing = []

    if settings.OPA_AUTH_TYPE == OPA_AUTH_TYPES.CERTIFICATE:
        if not settings.OPA_AUTH_CLIENT_CERT:
            cert_settings_missing += ['OPA_AUTH_CLIENT_CERT']
        if not settings.OPA_AUTH_CLIENT_KEY:
            cert_settings_missing += ['OPA_AUTH_CLIENT_KEY']
        if not settings.OPA_AUTH_CA_CERT:
            cert_settings_missing += ['OPA_AUTH_CA_CERT']

        if cert_settings_missing:
            raise PolicyEvaluationError(_('Following certificate settings are missing for OPA_AUTH_TYPE=Certificate: {}').format(cert_settings_missing))

    try:
        with opa_client(headers=headers) as client:
            try:
                response = client.query_rule(input_data=input_data, package_path='job_template', rule_name='response')
            except HTTPError as e:
                message = _('Call to OPA failed. Exception: {}').format(e)
                try:
                    error_data = e.response.json()
                except ValueError:
                    raise PolicyEvaluationError(message)

                error_code = error_data.get("code")
                error_message = error_data.get("message")
                if error_code or error_message:
                    message = _('Call to OPA failed. Code: {}, Message: {}').format(error_code, error_message)
                raise PolicyEvaluationError(message)
            except Exception as e:
                raise PolicyEvaluationError(_('Call to OPA failed. Exception: {}').format(e))

            result = response.get('result')
            if result is None:
                raise PolicyEvaluationError(_('Call to OPA did not return a "result" property. The path refers to an undefined document.'))

            result_serializer = OPAResultSerializer(data=result)
            if not result_serializer.is_valid():
                raise PolicyEvaluationError(_('OPA policy returned invalid result.'))

            result_data = result_serializer.validated_data
            if not result_data["allowed"]:
                violations = result_data.get("violations", [])
                raise PolicyEvaluationError(_('OPA policy denied the request, Violations: {}').format(violations))
    except Exception as e:
        raise PolicyEvaluationError(_('Policy evaluation failed, Exception: {}').format(e))
