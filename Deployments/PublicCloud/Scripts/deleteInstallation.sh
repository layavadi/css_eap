#!/bin/bash
#set -e

# MUST be set in environment variable
# CLUSTER_CRN=""
# KUBECONFIG=""

# OPTIONAL VARIABLES in environment  - with default value
# CDP_PROFILE=""
l_CSS_NAMESPACE=${CSS_NAMESPACE:-"css"}

CLUSTER_VERSION=0
PROFILE_TEXT="--profile $CDP_PROFILE"

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
if [ -z "$CLUSTER_CRN" ] || [ -z "$KUBECONFIG" ]; then
  echo "Variable CLUSTER_CRN, CDP_PATH, KUBECONFIG must be set"
  echo " "
  echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
  exit 1
else
  echo "CLUSTER_CRN value is $CLUSTER_CRN"
  echo "KUBECONFIG value is $KUBECONFIG"
fi


if [ -z "$CDP_PROFILE" ]; then
  echo "Variable CDP_PROFILE is not set, working with cdpcli without the profile"
else
  echo "CDP_PROFILE value is => $CDP_PROFILE"
fi

if [ -z "$CSS_NAMESPACE" ]; then
  echo "Variable CSS_NAMESPACE is not set, working with default value => $l_CSS_NAMESPACE"
else
  echo "CSS_NAMESPACE value is => $l_CSS_NAMESPACE"
fi
echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# setting the cluster version
set_cluster_version() {
  local command="cdp compute describe-cluster --cluster-crn $CLUSTER_CRN "
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  output=`eval $command | jq -r '.clusterStateVersion'`
  CLUSTER_VERSION=$output
  echo "     GOT THE CLUSTER STATE VERSION >> $CLUSTER_VERSION"
}

# verify the cluster state, and wait until it is in running state
verify_running() {
  local command="cdp compute describe-cluster --cluster-crn $CLUSTER_CRN"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
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

delete_helm_charts() {
  local dashboard_uninstall_command="helm uninstall opensearch-dashboards -n $l_CSS_NAMESPACE"
  local ml_uninstall_command="helm uninstall opensearch-ml -n $l_CSS_NAMESPACE"
  local ingest_uninstall_command="helm uninstall opensearch-ingest -n $l_CSS_NAMESPACE"
  local data_uninstall_command="helm uninstall opensearch-data -n $l_CSS_NAMESPACE"
  local master_uninstall_command="helm uninstall opensearch-master -n $l_CSS_NAMESPACE"

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $dashboard_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $dashboard_uninstall_command

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $ingest_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $ingest_uninstall_command

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $ml_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $ml_uninstall_command

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $data_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $data_uninstall_command

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $master_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $master_uninstall_command

  echo "Charts are deleted"
  sleep 20
}

delete_instancegroup() {
  set_cluster_version
  local instance_group_name="$1"
  local command="cdp compute delete-instance-group --cluster-crn $CLUSTER_CRN --instance-group-name $instance_group_name --cluster-state-version $CLUSTER_VERSION"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Running => $command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $command
}

delete_cluster() {
  local command="cdp compute delete-cluster --cluster-crn $CLUSTER_CRN"
  if [ -n "$CDP_PROFILE" ]; then
    command="$command $PROFILE_TEXT"
  fi
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Running => $command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $command
}

delete_helm_charts
verify_running "Deleting Helm Charts"
set_cluster_version

delete_instancegroup "css-ingest"
verify_running "Deleting Instancegroup css-ingest"
delete_instancegroup "css-ml"
verify_running "Deleting Instancegroup css-ml"
delete_instancegroup "css-master"
verify_running "Deleting Instancegroup css-master"
delete_instancegroup "css-data"
verify_running "Deleting Instancegroup css-data"
delete_cluster
echo "XX======================================================================XX==========================================================================XX"
echo "  All delete cluster related commands have been executed sucessfully. Please monitor the cluster state in the CDP UI."
echo "  CLUSTER_CRN $CLUSTER_CRN"
echo "  ENVIRONMENT_CRN $ENVIRONMENT_CRN"
echo "XX======================================================================XX==========================================================================XX"
