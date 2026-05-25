{{/*
Expand the name of the chart.
*/}}
{{- define "projectforge.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "projectforge.fullname" -}}
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

{{- define "projectforge.labels" -}}
helm.sh/chart: {{ include "projectforge.fullname" . }}
app.kubernetes.io/name: {{ include "projectforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "projectforge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "projectforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
