"""
Auto-Quarantine — automatically isolates compromised EC2 instances
by applying a deny-all security group and revoking IAM access.
"""
import logging
import asyncio
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def _get_ec2():
    return boto3.client(
        "ec2",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def _get_iam():
    return boto3.client(
        "iam",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def _get_or_create_quarantine_sg(ec2, vpc_id: str) -> str:
    """
    Get or create a 'CloudSentinel-Quarantine' security group that denies all traffic.
    """
    try:
        resp = ec2.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": ["CloudSentinel-Quarantine"]},
                {"Name": "vpc-id", "Values": [vpc_id]},
            ]
        )
        if resp["SecurityGroups"]:
            return resp["SecurityGroups"][0]["GroupId"]
    except ClientError:
        pass

    # Create quarantine SG — no inbound or outbound rules
    resp = ec2.create_security_group(
        GroupName="CloudSentinel-Quarantine",
        Description="CloudSentinel automatic quarantine — deny all traffic",
        VpcId=vpc_id,
    )
    sg_id = resp["GroupId"]

    # Remove the default allow-all egress rule
    ec2.revoke_security_group_egress(
        GroupId=sg_id,
        IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    )

    logger.info(f"Created quarantine security group {sg_id}")
    return sg_id


async def auto_quarantine(threat) -> bool:
    """
    Quarantine the source host of a threat:
    1. Find EC2 instances matching the source IP.
    2. Replace their security groups with the deny-all quarantine SG.
    3. Add an identifying tag for audit trail.
    """
    if not settings.AWS_ACCESS_KEY_ID:
        logger.info("AWS credentials not configured — skipping auto-quarantine")
        return False

    loop = asyncio.get_event_loop()

    try:
        success = await loop.run_in_executor(None, _quarantine_sync, threat)
        return success
    except Exception as e:
        logger.error(f"Auto-quarantine failed for {threat.source_ip}: {e}")
        return False


def _quarantine_sync(threat) -> bool:
    ec2 = _get_ec2()
    source_ip = threat.source_ip

    # Find instances by private or public IP
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "private-ip-address", "Values": [source_ip]},
        ]
    )

    instances = [
        i
        for r in resp["Reservations"]
        for i in r["Instances"]
        if i["State"]["Name"] == "running"
    ]

    if not instances:
        logger.info(f"No running instance found for IP {source_ip}")
        return False

    for instance in instances:
        instance_id = instance["InstanceId"]
        vpc_id = instance.get("VpcId", "")

        # Get quarantine SG
        quarantine_sg = _get_or_create_quarantine_sg(ec2, vpc_id)

        # Replace all security groups with quarantine SG
        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[quarantine_sg],
        )

        # Tag for audit trail
        ec2.create_tags(
            Resources=[instance_id],
            Tags=[
                {"Key": "CloudSentinel:Quarantined", "Value": "true"},
                {"Key": "CloudSentinel:ThreatId", "Value": threat.id},
                {"Key": "CloudSentinel:Severity", "Value": threat.severity},
                {"Key": "CloudSentinel:QuarantinedAt", "Value": threat.created_at.isoformat()},
            ],
        )

        logger.warning(
            f"QUARANTINED instance {instance_id} (IP={source_ip}) "
            f"for threat {threat.id} [{threat.severity}]"
        )

    return True