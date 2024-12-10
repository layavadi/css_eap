#!/bin/bash
set -e

####################################################################################
# BEFORE you start running the script
# jq should be installed
# To install jq run this command [this works in mac] => brew install jq
# CDP should be installed
# kubectl should be installed
# helm should be installed
# ~/.kube should be there on your system
####################################################################################

# MUST be set in environment variable
# CLUSTER_CRN=""
# HELM_CHARTS_DIRECTORY=""

# OPTIONAL VARIABLES in environment - with default value
# CDP_PROFILE=""
# l_CERT_MANAGER_NAMESPACE=${CERT_MANAGER_NAMESPACE:-"cert-manager"}
l_CSS_NAMESPACE=${CSS_NAMESPACE:-"css"}
l_ADMIN_PASSWORD=${ADMIN_PASSWORD:-"Cloudera@Test4321"}

helmcharts=("opensearch" "opensearch-dashboards")
helmdirectory="$HELM_CHARTS_DIRECTORY"
kubeconfigfile="$HOME/.kube/script-config"
kubeconfigfilearchive="$HOME/.kube/script-config-archive"

# If we turn on pull helm charts then we need these variable
# helmdirectory="css-helm-charts"
# helmdirectoryarchive="css-helm-charts-archive"
# REPOSITORY_URL="$REPOSITORY_BASE_URL/$CSS_REPO_PATH/"

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
if [ -z "$CLUSTER_CRN" ] || [ -z "$HELM_CHARTS_DIRECTORY" ]; then
  echo "Variable CLUSTER_CRN, HELM_CHARTS_DIRECTORY must be set"
  echo " "
  echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
  exit 1
else
  echo "CLUSTER_CRN value is => $CLUSTER_CRN"
  echo "HELM_CHARTS_DIRECTORY value is => $HELM_CHARTS_DIRECTORY"
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

if [ -z "$ADMIN_PASSWORD" ]; then
  echo "Variable ADMIN_PASSWORD is not set, working with default value => $l_ADMIN_PASSWORD"
else
  echo "ADMIN_PASSWORD value is => $l_ADMIN_PASSWORD"
fi

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

dashboard_credential_str=$(cat <<-END
config:
  opensearch_dashboards.yml: |
    opensearch:
      ssl:
        verificationMode: none
      username: admin
      password: $l_ADMIN_PASSWORD
END
)

# Function to generate kube config file
generate_kubeconfig() {
  echo "Generating kube config ========================================================================================================================="
  if [ -f "$kubeconfigfile" ]; then
    echo "$kubeconfigfile File already exists, archiving it"
    mv "$kubeconfigfile" "$kubeconfigfilearchive"
  fi
  local command=""
  if [ -n "$CDP_PROFILE" ]; then
    command="cdp compute get-kube-config --cluster-crn $CLUSTER_CRN --service computex --namespace computex  $PROFILE_TEXT | jq -r '.content' | sed 's/\\n/\n/g' > $kubeconfigfile"
  else
    command="cdp compute get-kube-config --cluster-crn $CLUSTER_CRN --service computex --namespace computex | jq -r '.content' | sed 's/\\n/\n/g' > $kubeconfigfile"
  fi

  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  echo "     Executing >> $command"
  echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
  eval "$command"
  if [ $? -eq 0 ]; then
    echo "kube config file successfully downloaded from the Cluster, now exporting it to KUBECONFIG"
  else
    echo "!!!! kube config file download failed !!!!"
    echo "!!!! need to evaluate last command !!!!"
    return 1
  fi
  echo "================================================================================================================================================"
}
# Function to pull and expand the helm charts
pull_and_expand_charts() {
  echo "Pulling and expanding charts ==================================================================================================================="
  if [ -d "$helmdirectory" ]; then
    echo "$helmdirectory directory already exists, archiving it"
    mv $helmdirectory $helmdirectoryarchive
  fi
  echo "Making Directory $helmdirectory"
  mkdir $helmdirectory
  cd $helmdirectory
  echo "Copying the charts in css-helm-charts"
  for chart in "${helmcharts[@]}"
  do
    local command="helm pull $REPOSITORY_URL$chart --version $HELM_VERSION"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $command
    if [ $? -eq 0 ]; then
      echo "$chart successfully downloaded, now extracting"
      tar -xvf "$chart-$HELM_VERSION.tgz"
    else
      echo "!!!! $chart download failed !!!!"
      return 1
    fi
  done
  echo "================================================================================================================================================"
}
# Function to install helm charts
install_charts() {
  echo "Installing charts =============================================================================================================================="
  cd $helmdirectory
  echo "We are in => $helmdirectory"
  echo "Using this kube file => $KUBECONFIG"
    printf "%s" "$dashboard_credential_str" > opensearch-dashboards/credentials.yaml

    local master_install_command="helm install opensearch-master opensearch -f opensearch/values.yaml -f opensearch/master.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace"
    local data_install_command="helm install opensearch-data opensearch -f opensearch/values.yaml -f opensearch/data.yaml --set adminPassword=$l_ADMIN_PASSWORD --set coordinatorService=data --namespace $l_CSS_NAMESPACE --create-namespace"
    local dashboard_install_command="helm install opensearch-dashboards opensearch-dashboards -f opensearch-dashboards/credentials.yaml --namespace $l_CSS_NAMESPACE --create-namespace"
    local mlnode_install_command="helm install opensearch-ml opensearch -f opensearch/values.yaml -f opensearch/ml.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace"
    local ingest_install_command="helm install opensearch-ingest opensearch -f opensearch/values.yaml -f opensearch/ingest.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace"

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $master_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $master_install_command
    sleep 10

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $data_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $data_install_command
    sleep 10

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $mlnode_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $mlnode_install_command
    sleep 10

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $ingest_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $ingest_install_command
    echo "############ Sleeping for a minute, let the initilisation of the pod happen ############"
    sleep 60

    echo "$dashboard_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $dashboard_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $dashboard_install_command

    echo "================================================================================================================================================"
    kubectl get pods -n "$l_CSS_NAMESPACE"

  echo "================================================================================================================================================"
}

generate_kubeconfig
export KUBECONFIG=$kubeconfigfile
install_charts

echo "XX==========================================================================XX==============================================================================XX"
echo "  CSS Helm charts are deployed successfully, kubeconfig file availaible at $kubeconfigfile, Please follow rest of the instructions."
echo "  You can query the open search endpoint now, below is the example"
echo "  curl -k 'http://<DATA_EXTERNAL_IP>:9200/_cat/indices' -u admin:$l_ADMIN_PASSWORD"
echo "  You can access dashboard in your browser by accessing this url => http://<DASHBOARD_EXTERNAL_IP>:5601"
echo "  For accessing Dashboard username: admin, password: $l_ADMIN_PASSWORD"
echo "XX==========================================================================XX==============================================================================XX"
