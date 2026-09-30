.DEFAULT_GOAL := help
.PHONY: requirements

# include *.mk

# Generates a help message. Borrowed from https://github.com/pydanny/cookiecutter-djangopackage.
help: ## Display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@perl -nle'print $& if m{^[\.a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m %-25s\033[0m %s\n", $$1, $$2}'

lang_targets = en es_419
_extract_translations:
	pybabel extract -F course_classification/locale/babel.cfg -o course_classification/locale/django.pot --msgid-bugs-address=eol-ing@uchile.cl --copyright-holder='Oficina EOL' --project=eol-vimeo --version=1.0.0 --last-translator='Oficina EOL <eol-ing@uchile.cl>' *
	pybabel extract -F course_classification/locale/babel-js.cfg -o course_classification/locale/django-js.pot --msgid-bugs-address=eol-ing@uchile.cl --copyright-holder='Oficina EOL' --project=eol-vimeo --version=1.0.0 --last-translator='Oficina EOL <eol-ing@uchile.cl>' *

create_translations_catalogs: _extract_translations ## Create the initial configuration of .po files for translation
	for lang in $(lang_targets) ; do \
		pybabel init -i course_classification/locale/django.pot -D django -d course_classification/locale/ -l $$lang ; \
		pybabel init -i course_classification/locale/django-js.pot -D djangojs -d course_classification/locale/ -l $$lang ; \
	done

update_translations: _extract_translations ## update strings to be translated
	pybabel update -N -D django -i course_classification/locale/django.pot -d course_classification/locale/
	pybabel update -N -D djangojs -i course_classification/locale/django-js.pot -d course_classification/locale/
	rm course_classification/locale/django.pot
	rm course_classification/locale/django-js.pot

compile_translations: ## compile .po files into .mo files
	pybabel compile -f -D django -d course_classification/locale/; \
	pybabel compile -f -D djangojs -d course_classification/locale/
