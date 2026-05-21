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

{{- define "projectforge.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "projectforge.labels" -}}
helm.sh/chart: {{ include "projectforge.chart" . }}
{{ include "projectforge.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: projectforge-ai
{{- end }}

{{- define "projectforge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "projectforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "projectforge.backend.selectorLabels" -}}
{{ include "projectforge.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- define "projectforge.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "projectforge.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "projectforge.image" -}}
{{- $registry := .Values.global.imageRegistry -}}
{{- $repo := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end }}

{{- define "projectforge.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "projectforge.fullname" .) }}
{{- end }}

{{- define "projectforge.redis.fullname" -}}
{{- printf "%s-redis" (include "projectforge.fullname" .) }}
{{- end }}

{{- define "projectforge.neo4j.fullname" -}}
{{- printf "%s-neo4j" (include "projectforge.fullname" .) }}
{{- end }}

{{- define "projectforge.databaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql+asyncpg://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "projectforge.postgresql.fullname" . }}:{{ .Values.postgresql.service.port }}/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{- .Values.backend.externalDatabaseUrl | default "" -}}
{{- end -}}
{{- end }}
