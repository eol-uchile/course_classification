# Python Standard Libraries
import json
import logging

# Installed packages (via pip)
from django.test.client import RequestFactory
from .models import CourseCategory, CourseClassification
from .helpers import get_courses_by_category
# Internal project dependencies
from .views import course_discovery_eol

logger = logging.getLogger(__name__)

def get_course_ctgs():
    """
        Return courses that are featured
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

def get_courses_filtered_by_course_state(course_state_list):
    """
        Return courses filter by course_state
    """
    factory = RequestFactory()
    data = {
        'search_string': '',
        'order_by': '',
        'year': '',
        'state': '',
        'classification': '',
        'page_size': '20',
        'page_index': '0'
    }
    # Request call using data parameters
    request = factory.post('/course_classification/search/', data=data)
    response = course_discovery_eol(request)
    results = json.loads(response.content)
    # Get courses from results
    courses = results["results"]
    # Filter courses by specific course_state 
    courses_filtered = []
    for course in courses:
        if course["course_state"] in course_state_list:
            courses_filtered.append(course)
    return courses_filtered

def get_all_categories_and_its_courses(courses):
    """
        Return all categories and its courses
    """
    ret_courses = {}
    categories = []
    for category in CourseCategory.objects.all().order_by('sequence'):
        categories.append({'id':category.id,'name':category.name,'seq':category.sequence,'show_opt':category.show_opt})
        ret_courses[category.id] = {'id':category.id,'name':category.name,'seq':category.sequence,'courses':[]}
        courses_ids = get_courses_by_category(category.id)
        courses_by_category=[]
        for course in courses:
            if course.pk in courses_ids:
                courses_by_category.append(course)
        ret_courses[category.id]['courses'] = courses_by_category
    return categories, ret_courses
