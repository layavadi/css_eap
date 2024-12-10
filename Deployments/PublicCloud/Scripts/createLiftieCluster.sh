#!/bin/bash
set -e

####################################################################################
# BEFORE you start running the script
# jq should be installed
# To install jq run this command [this works in mac] => brew install jq
# CDP should be installed
# In CDP we need to have describe-cluster, create-cluster, create-instance-groups should be public facing in compute service
# We also need to have clusterStateVersion and status in describe-cluster output
####################################################################################

# ENVIRONMENT_CRN=""
# CLUSTER_NAME=""
#

# OPTIONAL
# AUTHORIZED_IP_RANGES=""
# CDP_PROFILE=""

CLUSTER_CRN=""
CLUSTER_VERSION=0
PROFILE_TEXT="--profile $CDP_PROFILE"
CU_KMS_KEY_ARN=""

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
if [ -z "$ENVIRONMENT_CRN" ] || [ -z "$CLUSTER_NAME" ]; then
  echo "Variable ENVIRONMENT_CRN, CLUSTER_NAME must be set"
  echo " "
  echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
  exit 1
else
  echo "ENVIRONMENT_CRN value is $ENVIRONMENT_CRN"
  echo "CLUSTER_NAME value is $CLUSTER_NAME"
fi

if [ -z "$CDP_PROFILE" ]; then
  echo "Variable CDP_PROFILE is not set, working with cdpcli without the profile"
else
  echo "CDP_PROFILE value is => $CDP_PROFILE"
fi

if [ -z "$AUTHORIZED_IP_RANGES" ]; then
  echo "Variable AUTHORIZED_IP_RANGES is not set, will not update ip ranges in the cluster"
else
  echo "AUTHORIZED_IP_RANGES value is => $AUTHORIZED_IP_RANGES"
fi

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# setting the cluster version
set_cluster_version() {
  local command="cdp compute describe-cluster --cluster-crn $CLUSTER_CRN"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> eval $command | jq -r '.clusterStateVersion'"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  output=`eval $command | jq -r '.clusterStateVersion'`
  CLUSTER_VERSION=$output
  echo $CLUSTER_VERSION
}

set_kms_key() {
  local command="cdp compute describe-cluster --cluster-crn $CLUSTER_CRN"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> eval $command | jq -r '.eks.security.secretEncryption.customerKmsKeyArn'"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  output=`eval $command | jq -r '.eks.security.secretEncryption.customerKmsKeyArn'`
  CU_KMS_KEY_ARN=$output
  echo $CU_KMS_KEY_ARN
}

# creating the compute cluster
create_cluster() {
  local command="cdp compute create-cluster --environment $ENVIRONMENT_CRN --name $CLUSTER_NAME"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> eval $command | jq -r '.clusterCrn'"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  output=`eval $command`
  echo $output
  if echo $output | grep 'An error occurred'; then
    return 1
  else
    crn=`eval echo '$output' | jq -r '.clusterCrn'`
    CLUSTER_CRN=$crn
    echo $CLUSTER_CRN
  fi
}

# verify the cluster state, and wait until it is in running state
verify_running() {
  local command="cdp compute describe-cluster --cluster-crn $CLUSTER_CRN"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT "
  fi
  for i in {1..50}
  do
    output=`eval $command | jq -r '.status'`
    if [ "$output" = "RUNNING" ]; then
      break
    fi
    echo "$1 in progress..."
    sleep 60
  done
}

# creating the required liftie instance group 3 masters and 1 data
create_instancegroup() {
  local command="cdp compute create-instance-groups --cli-input-json '{
      \"clusterCrn\": \"$CLUSTER_CRN\",
      \"instanceGroups\": [
          {
              \"name\": \"css-master\",
              \"instanceCount\": 3,
              \"autoscaling\": {
                  \"maxInstance\": 3,
                  \"minInstance\": 3,
                  \"enabled\": true
              },
              \"instanceTier\": \"ON_DEMAND\",
              \"labels\": {
                  \"project\": \"css\",
                  \"css-node-group\": \"master\"
              },
              \"rootVolume\": {
                  \"size\": 50
              },
              \"instanceTypes\": [
                  \"m5.xlarge\"
              ]
          },
          {
              \"name\": \"css-data\",
              \"instanceCount\": 1,
              \"autoscaling\": {
                  \"maxInstance\": 1,
                  \"minInstance\": 1,
                  \"enabled\": true
              },
              \"instanceTier\": \"ON_DEMAND\",
              \"labels\": {
                  \"project\": \"css\",
                  \"css-node-group\": \"data\"
              },
              \"rootVolume\": {
                  \"size\": 50
              },
              \"instanceTypes\": [
                  \"m5.xlarge\"
              ]
          },
          {
              \"name\": \"css-ml\",
              \"instanceCount\": 1,
              \"autoscaling\": {
                  \"maxInstance\": 1,
                  \"minInstance\": 1,
                  \"enabled\": true
              },
              \"instanceTier\": \"ON_DEMAND\",
              \"labels\": {
                  \"project\": \"css\",
                  \"css-node-group\": \"ml\"
              },
              \"rootVolume\": {
                  \"size\": 50
              },
              \"instanceTypes\": [
                  \"m5.xlarge\"
              ]
          },
          {
              \"name\": \"css-ingest\",
              \"instanceCount\": 1,
              \"autoscaling\": {
                  \"maxInstance\": 1,
                  \"minInstance\": 1,
                  \"enabled\": true
              },
              \"instanceTier\": \"ON_DEMAND\",
              \"labels\": {
                  \"project\": \"css\",
                  \"css-node-group\": \"ingest\"
              },
              \"rootVolume\": {
                  \"size\": 50
              },
              \"instanceTypes\": [
                  \"m5.xlarge\"
              ]
          }
      ],
      \"clusterStateVersion\": $CLUSTER_VERSION,
      \"skipValidation\": false
  }'"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  eval $command
}

# currently this is breaking in dev for some entitlement, but we may perform manual steps for the same.
add_authorized_iprange_control_plane(){
  if [ -z "$AUTHORIZED_IP_RANGES" ]; then
    echo "############################# AUTHORIZED_IP_RANGES not set, we don't set in the cluster #############################"
    return 0
  fi
  set_kms_key
  set_cluster_version
  if [ -z "$CU_KMS_KEY_ARN" ]; then
    echo "############################# Not able to set CU_KMS_KEY_ARN, Please do it manually to access the control plane services #############################"
    return 0
  fi
  local command="cdp compute update-cluster --cluster-state-version $CLUSTER_VERSION --cli-input-json '{
   	\"clusterCrn\": \"$CLUSTER_CRN\",
   	\"spec\": {
       	\"security\": {
                   	\"apiServer\": {
                       	\"authorizedIpRanges\": [
                           	\"$AUTHORIZED_IP_RANGES\"
                       	],
                       	\"enabled\": true
                   	},
                   	\"secretEncryption\": {
                       	\"customerKmsKeyArn\": \"$CU_KMS_KEY_ARN\",
                       	\"enabled\": true
                   	},
                   	\"volumeEncryption\": {},
                   	\"private\": false
               	}
  	}}'
  "
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  eval $command
}

create_cluster
verify_running "Create Cluster"
set_cluster_version
create_instancegroup
sleep 20
verify_running "Create Instancegroup"
add_authorized_iprange_control_plane
verify_running "Add Security Block"
echo "XX======================================================================XX==========================================================================XX"
echo "   Now the cluster is created with the required instance groups, please follow the instruction to create the helm chart deployments for CSS."
echo "   CLUSTER_CRN $CLUSTER_CRN"
echo "XX======================================================================XX==========================================================================XX"
