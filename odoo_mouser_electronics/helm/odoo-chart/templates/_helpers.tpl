{{- define "odoo-mouser-electronics.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "odoo-mouser-electronics.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "odoo-mouser-electronics.name" . -}}
{{- end -}}
{{- end -}}

{{- define "odoo-mouser-electronics.labels" -}}
app.kubernetes.io/name: {{ include "odoo-mouser-electronics.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "odoo-mouser-electronics.selectorLabels" -}}
app.kubernetes.io/name: {{ include "odoo-mouser-electronics.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
