# Course Classification

![Coverage Status](/coverage-badge.svg)

![https://github.com/eol-uchile/course_classification/actions](https://github.com/eol-uchile/course_classification/workflows/Python%20application/badge.svg)

Courses classification by main classification and categories

# Install App

    docker-compose exec lms pip install -e /openedx/requirements/course_classification
    docker-compose exec cms pip install -e /openedx/requirements/course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations course_classification
    docker-compose exec lms python manage.py lms --settings=prod.production migrate course_classification


## Settings
 These values can be overridden on a per-site basis through **Site Configuration** using **SiteHelpers**, allowing site-specific customization without modifying the platform's global settings.

### `EXPLORE_COURSES_PAGE_SIZE`

The number of courses displayed per page in the **Explore Courses** view.

**Default value:** `20`

```python
EXPLORE_COURSES_PAGE_SIZE = 20
```

### `MAX_ELASTICSEARCH_PAGE_SIZE`

The maximum number of results that can be requested in a single Elasticsearch query.

**Default value:** `200`

```python
MAX_ELASTICSEARCH_PAGE_SIZE = 200
```

### `COURSE_SEARCH_INITIAL_YEAR`

The starting year used by course search features when filtering or querying course data.

**Default value:** `2020`

```python
COURSE_SEARCH_INITIAL_YEAR = 2020
```

### `COURSE_SEARCH_FUTURE_TIME_HORIZON`

The future time horizon used by course search to determine how far ahead upcoming courses should be considered.

The value is expressed in seconds.

**Default value:** `262080` (approximately 6 months)

```python
COURSE_SEARCH_FUTURE_TIME_HORIZON = 262080  # approximately 6 months
```

## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml
