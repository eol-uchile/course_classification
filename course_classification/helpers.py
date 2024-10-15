# -*- coding:utf-8 -*-
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory
from django.db.models import Q
from django.urls import reverse
from collections import OrderedDict
from datetime import datetime
from django.utils import timezone
from opaque_keys.edx.keys import CourseKey
from opaque_keys import InvalidKeyError
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
import logging
log = logging.getLogger(__name__)

def get_course_ctgs(courses):
    """
        Return dict with categories and its courses, sorted by proximity to today's date
    """
    ret_courses = OrderedDict()
    ret_courses['featured'] = []
    mc_courses= {}
    today = timezone.now()  # Get timezone-aware current datetime
    if CourseClassification.objects.filter(is_featured_course=True).exists():
        for course in courses:
            try:
                course_class = CourseClassification.objects.get(course_id=course.id)
                if course_class.is_featured_course:
                    ret_courses['featured'].append(course)
                    if course_class.MainClass:
                        days_left = (course.start_date - today).days
                        mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo, 'days_left': days_left}
            except CourseClassification.DoesNotExist:
                pass
        # Sort featured courses by proximity to today's date
        if ret_courses['featured']:
            ret_courses['featured'].sort(key=lambda course: abs((course.start_date - today).days))
            return ret_courses, mc_courses
    del ret_courses['featured']

    for main in CourseCategory.objects.all().order_by('sequence'):
        ret_courses[main.id] = {'id':main.id,'name':main.name, 'seq':main.sequence,'show_opt':main.show_opt, 'courses':[]}
    mc_courses= {}
    for course in courses:
        try:
            course_class = CourseClassification.objects.get(course_id=course.id)
            if course_class.MainClass:
                days_left = (course.start_date - today).days
                mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo,'days_left': days_left}
            for ctg in course_class.course_category.all():
                ret_courses[ctg.id]['courses'].append(course)
        except CourseClassification.DoesNotExist:
            pass
    # Sort courses in each category by proximity to today's date
    for ctg_id in ret_courses:
        ret_courses[ctg_id]['courses'].sort(key=lambda course: abs((course.start_date - today).days))
    return ret_courses, mc_courses

def get_featured_courses():
    """
        Return featured courses
    """
    courses = []
    mc_courses= {}
    if CourseClassification.objects.filter(is_featured_course=True).exists():
        cc = [x.course_id for x in CourseClassification.objects.filter(is_featured_course=True)]
        courses = CourseOverview.objects.filter(id__in=cc, catalog_visibility="both")
        mc_courses = {
            x.course_id: {
                'name': x.MainClass.name, 
                'logo': x.MainClass.logo
                } for x in CourseClassification.objects.filter(is_featured_course=True) if x.MainClass}
    return courses, mc_courses

def get_all_logos():
    """
        Return the logo and URL of the institutions if institution have the template configured
    """
    logos = [
        [
            x.logo.url, 
            reverse('course_classification:institution', kwargs={'org_id':x.id}) if MainCourseClassificationTemplate.objects.filter(main_classification=x).exists() else None
        ] 
        for x in MainCourseClassification.objects.filter(is_active=True, visibility__in=[0,2]).exclude(logo="").order_by('sequence')
        ]
    return logos

def get_all_main_classifications():
    """
        Return all active main classification
    """
    orgs = [[x.id, x.name] for x in MainCourseClassification.objects.filter(is_active=True, visibility__in=[1,2]).order_by('sequence')]
    return orgs

def get_courses_by_classification(org_id):
    """
        Return list of courses by main classification
    """
    courses = list(CourseClassification.objects.filter(MainClass__id=org_id, MainClass__is_active=True).values('course_id'))
    course_ids = [x['course_id'] for x in courses]
    return course_ids

def set_data_courses(courses):
    """
        [
            {
                "_index": "courseware_index", 
                "_type": "course_info", 
                "_id": "course-v1:eol+Test202+2023", 
                "_score": 1.0, 
                "data": {
                    "id": "course-v1:eol+Test202+2023", 
                    "course": "course-v1:eol+Test202+2023", 
                    "content": {
                        "display_name": "Test202", 
                        "overview": "overview overview overview", 
                        "number": "Test202"
                        }, 
                    "image_url": "/asset-v1:eol+Test202+2023+type@asset+block@default-course2.png", 
                    "start": "2030-01-01T00:00:00+00:00", 
                    "number": "Test202", 
                    "org": "eol", 
                    "modes": ["audit"], 
                    "language": "en"
                }, 
                "score": 1.0
            }, {...},{...},{...}
        ]
    """
    course_ids = [CourseKey.from_string(c['_id']) for c in courses]
    main_classifications = {
        str(x.course_id) : {
            'name':x.MainClass.name, 
            'logo':'' if not x.MainClass.logo else x.MainClass.logo.url 
            }
        for x in CourseClassification.objects.filter(course_id__in=course_ids).exclude(MainClass=None) 
        }
    course_overviews = {
        str(x['id']) : {
            'short_description' : x['short_description'], 
            'advertised_start' : x['advertised_start'], 
            'display_org_with_default' : x['display_org_with_default']
            } 
        for x in list(CourseOverview.objects.filter(id__in=course_ids).values('id', 'short_description', 'advertised_start', 'display_org_with_default'))
        }
    new_data = []
    for course in courses:
        course['extra_data'] = course_overviews.get(course['_id'], {})
        course['extra_data']['main_classification'] = main_classifications.get(course['_id'], {})
        new_data.append(course)
    return new_data
