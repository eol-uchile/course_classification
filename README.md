# Course Classification

![https://github.com/eol-uchile/course_classification/actions](https://github.com/eol-uchile/course_classification/workflows/Python%20application/badge.svg)

Courses classification by main classification and categories

# Install App

    docker-compose exec lms pip install -e /openedx/requirements/course_classification
    docker-compose exec cms pip install -e /openedx/requirements/course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production migrate course_classification


## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/course_classification/.github/test.sh
