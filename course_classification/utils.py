# Python Standard Libraries
import json
import logging
from collections import OrderedDict
from .models import CourseClassification

# Installed packages (via pip)
from django.test.client import RequestFactory

# Internal project dependencies
from .views import course_discovery_eol

logger = logging.getLogger(__name__)
   

def get_course_ctgs():
    """
        Return dict with categories and its courses
    """
    factory = RequestFactory()
    data = {
        'search_string': '',
        'order_by': '',
        'year': '',
        'state': '',
        'classification': '',
        'page_size': '20',
        'page_index': '0',
        'featured': 'True'
    }
    # Request call using data parameters
    request = factory.post('/course_classification/search/', data=data)
    response = course_discovery_eol(request)
    results = json.loads(response.content)
    # Get courses from results
    return results["results"]
