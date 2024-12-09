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
# ~/.ssh should be there on your system
####################################################################################

# MUST be set in environment variable
# ECS_SERVER_HOST=""
# KUBECONFIG=""
# HELM_CHARTS_DIRECTORY=""

# If we turn on pull helm charts then we need these variable
# HELM_VERSION="0.1.0-b28"
# REPOSITORY_BASE_URL="oci://docker-private.infra.cloudera.com"
# CSS_REPO_PATH="cloudera-helm/solr"
# REPOSITORY_URL="$REPOSITORY_BASE_URL/$CSS_REPO_PATH/"

# OPTIONAL VARIABLE in environemnt variable - with default value
l_CSS_NAMESPACE=${CSS_NAMESPACE:-"css"}
l_ADMIN_PASSWORD=${ADMIN_PASSWORD:-"Cloudera@Test4321"}

helmcharts=("opensearch" "opensearch-dashboards")
helmdirectory="$HELM_CHARTS_DIRECTORY"
#helmdirectoryarchive="css-helm-charts-archive"
kubeconfigfile="$KUBECONFIG"

strtobereplaced="example.vpc.cloudera.com"

echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
if [ -z "$ECS_SERVER_HOST" ] || [ -z "$KUBECONFIG" ] || [ -z "$HELM_CHARTS_DIRECTORY" ]; then
  echo "Variable ECS_SERVER_HOST, KUBECONFIG, HELM_CHARTS_DIRECTORY must be set"
  exit 1
else
  echo "ECS_SERVER_HOST value is => $ECS_SERVER_HOST"
  echo "KUBECONFIG value is => $KUBECONFIG"
  echo "HELM_CHARTS_DIRECTORY value is => $HELM_CHARTS_DIRECTORY"
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
modify_kubeconfig() {
  echo "Modifying kube config ========================================================================================================================="
  echo "changing the occurences of 127.0.0.1 with the value $ECS_SERVER_HOST from this file $kubeconfigfile"
  kubeconfigcontent=$(<$kubeconfigfile)
  echo "${kubeconfigcontent//127.0.0.1/$ECS_SERVER_HOST}" > $kubeconfigfile
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

    opensearch_ingress=$(<opensearch/ecs-ingress.yaml)
    echo "${opensearch_ingress//$strtobereplaced/$ECS_SERVER_HOST}" > opensearch/ecs-ingress.yaml

    local master_install_command="helm install opensearch-master opensearch -f opensearch/values.yaml -f opensearch/master-pvcds.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace --set k8sProvider=ecs"
    local data_install_command="helm install opensearch-data opensearch -f opensearch/values.yaml -f opensearch/data-pvcds.yaml -f opensearch/ecs-ingress.yaml --set adminPassword=$l_ADMIN_PASSWORD --set coordinatorService=data --namespace $l_CSS_NAMESPACE --create-namespace --set k8sProvider=ecs"
    local ml_install_command="helm install opensearch-ml opensearch -f opensearch/values.yaml -f opensearch/ml-pvcds.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace --set k8sProvider=ecs"
    local ingest_install_command="helm install opensearch-ingest opensearch -f opensearch/values.yaml -f opensearch/ingest-pvcds.yaml --set adminPassword=$l_ADMIN_PASSWORD --namespace $l_CSS_NAMESPACE --create-namespace --set k8sProvider=ecs"
    local dashboard_install_command="helm install opensearch-dashboards opensearch-dashboards -f opensearch-dashboards/credentials.yaml --namespace $l_CSS_NAMESPACE --set k8sProvider=ecs"

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
    echo "     Executing >> $ml_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $ml_install_command
    sleep 10

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $ingest_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $ingest_install_command
    echo "############ Sleeping for a minute, let the initilisation of the pod happen ############"
    sleep 60

    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    echo "     Executing >> $dashboard_install_command"
    echo "XXXX----------------------------------------------------------------------------------------------------------------------------------------XXXX"
    $dashboard_install_command
    echo "================================================================================================================================================"
    kubectl get pods -n "$l_CSS_NAMESPACE"
  echo "================================================================================================================================================"
}

modify_kubeconfig
install_charts

echo "XX==========================================================================XX==============================================================================XX"
echo "  CSS Helm charts are deployed successfully, kubeconfig file availaible at $kubeconfigfile, Please follow rest of the instructions."
echo "  You can query the open search endpoint now, below is the example"
echo "  curl -k 'http://opensearch-cluster.$ECS_SERVER_HOST:80/_cat/indices' -u admin:$l_ADMIN_PASSWORD"
echo "  You may need to do port forward for the dashboard to access, command => kubectl port-forward service/opensearch-dashboards 5601 -n css"
echo "XX==========================================================================XX==============================================================================XX"
