{{/*
Expand the name of the chart.
*/}}
{{- define "incident-bot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "incident-bot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "incident-bot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "incident-bot.labels" -}}
helm.sh/chart: {{ include "incident-bot.chart" . }}
{{ include "incident-bot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "incident-bot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "incident-bot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "incident-bot.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "incident-bot.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Environment variables formatter
*/}}
{{- define "incident-bot.envVarsFormatter" -}}
{{- range $key, $value := . }}
- name: {{ printf "%s" $key | upper | quote }}
  value: {{ $value | quote }}
{{- end -}}
{{- end -}}

{{/*
Rendered environment variables
*/}}
{{- define "incident-bot.envVars.rendered" -}}
{{- range $ctx := . }}
{{- if .envVars }}
{{- include "incident-bot.envVarsFormatter" .envVars }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Rendered base image
*/}}
{{- define "incident-bot.image.rendered" -}}
"{{ .Values.image.repository }}:v{{ .Values.image.tag | default .Chart.AppVersion }}{{ if .Values.image.suffix }}-{{ .Values.image.suffix}}{{ end }}"
{{- end }}

{{/*
Rendered util image
*/}}
{{- define "incident-bot.util-image.rendered" -}}
"{{ .Values.image.repository }}:util-v{{ .Values.init.image.tag | default .Chart.AppVersion }}{{ if .Values.image.suffix }}-{{ .Values.image.suffix}}{{ end }}"
{{- end }}
