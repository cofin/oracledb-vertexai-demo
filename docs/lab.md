# Hands-on Lab: Cymbal Coffee — Oracle 26ai + Vertex AI

Cymbal Coffee ships **two** hands-on labs. Pick the one that matches how you
want to run the demo — the simplest single-VM path, or a production-shaped
cloud architecture. Both paths assume a GCP account with billing/credits
enabled.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`server;1.1em` Single-VM GCE
:link: lab-gce
:link-type: doc

Everything on one Compute Engine VM — Oracle 26ai and the Litestar app side by
side. The fastest way to get the demo running.
:::

:::{grid-item-card} {octicon}`cloud;1.1em` Cloud Run
:link: lab-cloud-run
:link-type: doc

Production-shaped: the app on Cloud Run, a private GCE Oracle 26ai database,
and a Cloud Build deploy pipeline over a private VPC.
:::

::::
