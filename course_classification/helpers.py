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
    Return dict with categories and its courses, sorted by enrollment and date criteria.
    """
    ret_courses = OrderedDict()
    mc_courses= {}
    today = timezone.now()  # Get timezone-aware current datetime
    featured_courses = []
    if CourseClassification.objects.filter(is_featured_course=True).exists():
        for course in courses:
            try:
                course_class = CourseClassification.objects.get(course_id=course.id)
                course_start = getattr(course, 'start', None)
                if course_class.is_featured_course:
                    featured_courses.append(course)
                    if course_class.MainClass:
                        days_left = (course_start - today).days
                        mc_courses[course.id] = {'name': course_class.MainClass.name,'logo': course_class.MainClass.logo,'days_left': days_left}
                else:
                    if course_class.MainClass:
                        days_left = (course_start - today).days
                        mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo, 'days_left': days_left}
            except CourseClassification.DoesNotExist:
                pass
    if featured_courses:
        # Apply classification and sorting to featured courses
        ret_courses['featured'] = classify_and_sort_courses(featured_courses, today)
        # Early return to match original behavior
        return ret_courses, mc_courses

    # If no featured courses, proceed to build categories
    categories = CourseCategory.objects.all().order_by('sequence')
    if categories.exists():
        for main in categories:
            ret_courses[main.id] = {'id':main.id,'name':main.name, 'seq':main.sequence,'show_opt':main.show_opt, 'courses':[]}
        # Collect courses into categories
        for course in courses:
            try:
                course_class = CourseClassification.objects.get(course_id=course.id)
                course_start = getattr(course, 'start', None)
                if course_class.MainClass:
                    days_left = (course_start - today).days if course_start else None
                    mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo,'days_left': days_left}
                for ctg in course_class.course_category.all():
                    ret_courses[ctg.id]['courses'].append(course)
            except CourseClassification.DoesNotExist:
                pass
        # Apply classification and sorting to courses in each category
        for key in ret_courses:
            if key != 'featured':
                category_courses = ret_courses[key]['courses']
                ret_courses[key]['courses'] = classify_and_sort_courses(category_courses, today)
    else:
        # If no categories are found and no featured courses, ret_courses remains empty
        ret_courses = OrderedDict()
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

def classify_and_sort_courses(courses, today):
    """
    Classify and sort courses based on their state and proximity to the current date.
    """
    # Classify courses by state
    enrollable_courses = []
    upcoming_enrollable_courses = []
    upcoming_notenrollable_courses = []
    ongoing_notenrollable_courses = []
    completed_courses = []

    for course in courses:
        course_start = getattr(course, 'start', None)
        course_end = getattr(course, 'end', None)
        enroll_start = getattr(course, 'enrollment_start', course_start)
        enroll_end = getattr(course, 'enrollment_end', course_end)
        is_invitation_only = getattr(course, 'invitation_only', False)

        # Ensure that enroll_start and enroll_end are not None before comparisons
        # If enroll_start is None, set it to course_start
        if enroll_start is None:
            enroll_start = course_start
        # If enroll_end is None, set it to course_end or a future date
        if enroll_end is None:
            enroll_end = course_end if course_end else today.replace(year=today.year + 100)

        if is_invitation_only:
            if course_start > today:
                course.course_state = 'upcoming_notenrollable'
                upcoming_notenrollable_courses.append(course)
            else:
                course.course_state = 'ongoing_notenrollable'
                ongoing_notenrollable_courses.append(course)
        elif enroll_start <= today and (not enroll_end or enroll_end > today):
            if course_start <= today:
                course.course_state = 'enrollable'
                enrollable_courses.append(course)
            else:
                course.course_state = 'upcoming_enrollable'
                upcoming_enrollable_courses.append(course)
        elif course_start > today:
            course.course_state = 'upcoming_notenrollable'
            upcoming_notenrollable_courses.append(course)
        elif course_start <= today and (not course_end or course_end > today):
            course.course_state = 'ongoing_notenrollable'
            ongoing_notenrollable_courses.append(course)
        elif course_end and course_end <= today:
            course.course_state = 'completed'
            completed_courses.append(course)
        else:
            pass

    # Sorting each state group by proximity to the present
    def sort_key_start(course):
        if course.start:
            return abs((course.start - today).days)
        else:
            return float('inf')

    def sort_key_end(course):
        if course.end:
            return abs((course.end - today).days)
        else:
            return float('inf')

    enrollable_courses.sort(key=sort_key_start)
    upcoming_enrollable_courses.sort(key=sort_key_start)
    upcoming_notenrollable_courses.sort(key=sort_key_start)
    ongoing_notenrollable_courses.sort(key=sort_key_start)
    completed_courses.sort(key=sort_key_end)

    # Combine the lists
    sorted_courses = (
        enrollable_courses +
        upcoming_enrollable_courses +
        upcoming_notenrollable_courses +
        ongoing_notenrollable_courses +
        completed_courses
    )
    return sorted_courses











