
test:
	pip install -r requirements.txt
	nosetests --config=setup.cfg
	pip uninstall -r requirements.txt --yes

build:
	pip install .
	
run: build
	python saltbot

debug: clean test build
	python saltbot -v 0

clean:
	pip uninstall saltbot --yes

