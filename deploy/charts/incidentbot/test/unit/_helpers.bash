# chart_dir returns the directory for the chart

chart_dir() {
    echo ${BATS_TEST_DIRNAME}/../..
}

chart_version() {
    cd $(chart_dir) && echo $(cat Chart.yaml | yq '.version')
}
