.PHONY: install run run-api test dashboard docker
install:
	pip install -r requirements.txt
run:            ## offline run with synthetic sample data
	python -m pipeline.run --source sample
run-api:        ## live incremental run against the Chicago Data Portal
	python -m pipeline.run --source api --max-rows 100000
test:
	pytest -q
dashboard:
	streamlit run dashboard/app.py
docker:
	docker build -t chicago-311-pipeline . && docker run --rm -p 8501:8501 chicago-311-pipeline
