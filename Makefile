
ifndef TEST_LOCAL
	TEST_LOCAL=True
endif 

setup:
	-[[ "$(TEST_LOCAL)" == "True" ]] && bash ./saltbot/tests/test_db.sh setup
	pip install -r requirements.txt

build:
	pip install .

clean:
	pip uninstall -r requirements.txt --yes
	pip uninstall saltbot --yes
	-[[ "$(TEST_LOCAL)" == "True" ]] && bash ./saltbot/tests/test_db.sh cleanup

debug: setup
	-pytest -c pytest.ini

test: setup
	-pytest -c pytest.ini
	bash ./saltbot/tests/test_db.sh cleanup

run: build
	saltbot
