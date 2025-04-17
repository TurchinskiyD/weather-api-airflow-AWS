#!/bin/bash

set -e

INSTANCE_NAME="ec2-for-open-weather"
AMI_ID="ami-03f4878755434977f"  # ����� �� �������
INSTANCE_TYPE="t2.micro"
KEY_NAME="open-weather-key"
SECURITY_GROUP_ID="sg-0a1b2c3d4e5f67890"  # �������!
REGION="us-west-2"

echo "��������� EC2 ������� ($INSTANCE_NAME)..."

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SECURITY_GROUP_ID" \
  --region "$REGION" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --query "Instances[0].InstanceId" \
  --output text)

echo "������� ������ �������� $INSTANCE_ID..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
echo "EC2 ������� ��������: $INSTANCE_ID"

# ��������� Elastic IP
echo "��������� Elastic IP..."
ALLOCATION_ID=$(aws ec2 allocate-address --domain vpc --region "$REGION" --query "AllocationId" --output text)

# ����'���� Elastic IP �� EC2
echo "����'����� Elastic IP ($ALLOCATION_ID) �� EC2 ($INSTANCE_ID)..."
aws ec2 associate-address \
  --instance-id "$INSTANCE_ID" \
  --allocation-id "$ALLOCATION_ID" \
  --region "$REGION"

# �������� ������� IP-������
PUBLIC_IP=$(aws ec2 describe-addresses --allocation-ids "$ALLOCATION_ID" --region "$REGION" --query "Addresses[0].PublicIp" --output text)

echo "Elastic IP $PUBLIC_IP ����'����� �� $INSTANCE_NAME ($INSTANCE_ID)"
