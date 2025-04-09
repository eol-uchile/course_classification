# -*- coding:utf-8 -*-
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory
from django.db.models import Q
from django.urls import reverse
from collections import OrderedDict
from opaque_keys.edx.keys import CourseKey
from opaque_keys import InvalidKeyError
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
import logging
from django.utils import timezone
from datetime import datetime
import math
log = logging.getLogger(__name__)
    
def sort_key(course, today, key='start'):
    date = getattr(course, key, None)
    if date:
        return abs((date - today).days)
    else:
        return float('inf')

def set_time_left(course_start,today):
    days_left = (course_start - today).days
    year = math.trunc(days_left/365)
    month = math.trunc(days_left/30)
    if(year>0):
        time_left = [year,'y']
    elif(month>0 and month<=12):
        time_left = [month,'m']
    elif(days_left<=31):
        time_left = [days_left,'d']
    return time_left
    

def get_course_ctgs(courses):
    """
        Return dict with categories and its courses
    """
    ret_courses = OrderedDict()
    ret_courses['featured'] = []
    mc_courses= {}
    if CourseClassification.objects.filter(is_featured_course=True).exists():
        for course in courses:
            try:
                course_class = CourseClassification.objects.get(course_id=course.id)
                if course_class.is_featured_course:
                    ret_courses['featured'].append(course)
                    if course_class.MainClass:
                        mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo}
            except CourseClassification.DoesNotExist:
                pass
        if ret_courses['featured']:
            return ret_courses, mc_courses
    del ret_courses['featured']

    for main in CourseCategory.objects.all().order_by('sequence'):
        ret_courses[main.id] = {'id':main.id,'name':main.name, 'seq':main.sequence,'show_opt':main.show_opt, 'courses':[]}
    mc_courses= {}
    for course in courses:
        try:
            course_class = CourseClassification.objects.get(course_id=course.id)
            if course_class.MainClass:
                mc_courses[course.id] = {'name': course_class.MainClass.name, 'logo': course_class.MainClass.logo}
            for ctg in course_class.course_category.all():
                ret_courses[ctg.id]['courses'].append(course)
        except CourseClassification.DoesNotExist:
            pass
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
            'display_org_with_default' : x['display_org_with_default'],
            'invitation_only' : x['invitation_only']
            } 
        for x in list(CourseOverview.objects.filter(id__in=course_ids).values('id', 'short_description', 'advertised_start', 'display_org_with_default','invitation_only'))
        }
    today = timezone.now()
    new_data = []
    for course in courses:
        new_course = course["data"]
        course_start = new_course.get("start",None)
        new_course['time_left']= set_time_left(datetime.fromisoformat(course_start), today)
        new_course['course_state']= ""
        new_course['extra_data'] = course_overviews.get(course['_id'], {})
        new_course['extra_data']['main_classification'] = main_classifications.get(course['_id'], {})
        new_data.append(new_course)
    new_courses_data = classify_and_sort_courses_dict(new_data, today)
    return new_courses_data

def classify_and_sort_courses_dict(courses, today):
    """
    Classify and sort courses based on their state and proximity to the current date using a dictionary.
    """
    # Next variables are made by course state and enrollment state
    ongoing_enrollable_courses = []
    upcoming_enrollable_courses = []
    upcoming_notenrollable_courses = []
    ongoing_notenrollable_courses = []
    # Course completed
    completed_courses = []

    for course in courses:
        course_start = datetime.fromisoformat(course.get('start', None))
        course_end = course.get('end', None)
        if course_end is not None:
            course_end = datetime.fromisoformat(course_end)
        enroll_start = datetime.fromisoformat(course.get('enrollment_start')) if course.get('enrollment_start') else course_start
        enroll_end =  datetime.fromisoformat(course.get('enrollment_end')) if course.get('enrollment_end') else course_end
        extra_data = course.get('extra_data', None)
        if extra_data is not None:
            is_invitation_only = extra_data.get('invitation_only', False)
        else:
            is_invitation_only = False
        # Ensure that enroll_start and enroll_end are not None before comparisons
        # If enroll_start is None, set it to course_start
        if enroll_start is None:
            enroll_start = course_start
        # If enroll_end is None, set it to course_end or a future date
        if enroll_end is None:
            enroll_end =  course_end if course_end else today.replace(year=today.year + 100)
        # If has enrollment only by invitation
        if is_invitation_only:
            # If course is'nt started yet
            if course_start > today:
                course["course_state"] = 'upcoming_notenrollable'
                upcoming_notenrollable_courses.append(course)
            # course already start
            else:
                course["course_state"] = 'ongoing_notenrollable'
                ongoing_notenrollable_courses.append(course)
        # If today is between enrollment range and the course already started 
        elif enroll_start <= today and (enroll_end > today) and course_start <= today and (course_end is None or course_end > today):
            course["course_state"] = 'ongoing_enrollable'
            ongoing_enrollable_courses.append(course)
        # If you are not within the registration deadline today and the course has already begun
        elif enroll_start < today and (enroll_end < today) and course_start <= today and (course_end is None or course_end > today):
            course["course_state"] = 'ongoing_notenrollable'
            ongoing_notenrollable_courses.append(course)
        # If you are not within the registration deadline today and the course has not yet started
        elif enroll_start < today and (enroll_end < today) and course_start > today and (course_end is None or course_end > today):
            course["course_state"] = 'upcoming_notenrollable'
            upcoming_notenrollable_courses.append(course)
        # If you are within the enrollment range today and the course has not yet started
        elif enroll_start <= today and (enroll_end > today) and course_start > today:
            course["course_state"] = 'upcoming_enrollable'
            upcoming_enrollable_courses.append(course)
        # If you are not within the enrollment range today and the course has not yet started
        elif enroll_start > today and (enroll_end > today) and course_start > today:
            course["course_state"] = 'upcoming_notenrollable'
            upcoming_notenrollable_courses.append(course)
        # If today is after the end date of the course
        elif course_end is not None and course_end <= today:
            course["course_state"] = 'completed'
            completed_courses.append(course)
        else:
            course["course_state"] = 'other'
            completed_courses.append(course)

    ongoing_enrollable_courses.sort(key=lambda course: sort_key(course, today, key='start'))
    upcoming_enrollable_courses.sort(key=lambda course: sort_key(course, today, key='start'))
    upcoming_notenrollable_courses.sort(key=lambda course: sort_key(course, today, key='start'))
    ongoing_notenrollable_courses.sort(key=lambda course: sort_key(course, today, key='start'))
    completed_courses.sort(key=lambda course: sort_key(course, today, key='end'))

    # Combine the lists
    sorted_courses = (
        ongoing_enrollable_courses +
        upcoming_enrollable_courses +
        upcoming_notenrollable_courses +
        ongoing_notenrollable_courses +
        completed_courses
    )
    return sorted_courses