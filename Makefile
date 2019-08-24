
test:
	pip install -r requirements.txt
	nosetests --config=setup.cfg

build:
	pip install .

clean:
	pip uninstall -r requirements.txt --yes
	pip uninstall saltbot --yes
	
run: build
	saltbot

debug: clean test build
	python saltbot -v 0
