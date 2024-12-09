#!/bin/bash
set -e

# MUST be set in environment variable
# KUBECONFIG

# OPTIONAL VARIABLE in environemnt variable - with default value
l_CSS_NAMESPACE=${CSS_NAMESPACE:-"css"}

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

if [ -z "$CSS_NAMESPACE" ]; then
  echo "Variable CSS_NAMESPACE is not set, working with default value => $l_CSS_NAMESPACE"
else
  echo "CSS_NAMESPACE value is => $l_CSS_NAMESPACE"
fi

if [ -z "$KUBECONFIG" ]; then
  echo "Variable KUBECONFIG must be set"
  exit 1
else
  echo "KUBECONFIG value is => $KUBECONFIG"
fi
echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

delete_helm_charts() {
  local dashboard_uninstall_command="helm uninstall opensearch-dashboards -n $l_CSS_NAMESPACE"
  local ml_uninstall_command="helm uninstall opensearch-ml -n $l_CSS_NAMESPACE"
  local ingest_uninstall_command="helm uninstall opensearch-ingest -n $l_CSS_NAMESPACE"
  local data_uninstall_command="helm uninstall opensearch-data -n $l_CSS_NAMESPACE"
  local master_uninstall_command="helm uninstall opensearch-master -n $l_CSS_NAMESPACE"
  local css_namespace_uninstall_command="kubectl delete namespace $l_CSS_NAMESPACE"

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

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $css_namespace_uninstall_command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  $css_namespace_uninstall_command
}

delete_helm_charts

echo "XX======================================================================XX==========================================================================XX"
echo "  All charts are deleted. You can delete the Experience cluster and Base cluster if you don't need it further"
echo "XX======================================================================XX==========================================================================XX"
