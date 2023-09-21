# Course Classification

# Install App

    docker-compose exec lms pip install -e /openedx/requirements/course_classification
    docker-compose exec cms pip install -e /openedx/requirements/course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production migrate course_classification

