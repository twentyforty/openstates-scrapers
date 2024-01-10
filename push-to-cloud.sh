./use-remote-core.sh
gcloud builds submit --config cloudbuild-openstates-scrapers.yaml &
gcloud builds submit --config cloudbuild-openstates-scrapers-ca.yaml
