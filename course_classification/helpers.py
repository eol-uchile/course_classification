# -*- coding:utf-8 -*-
# Python Standard Libraries
from datetime import datetime
import json
import logging
import math

# Installed packages (via pip)
from django.urls import reverse
from django.utils import timezone

# Edx dependencies
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.course_modes.models import get_cosmetic_display_price
from lms.djangoapps.courseware.courses import get_course_by_id

# Internal project dependencies
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory


log = logging.getLogger(__name__)
    
def set_time_left(course_start,today):
    """
    Allows you to obtain how much time are left until a course start, can be in days, months or years
    """
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
        Return all active main classification that have courses
    """
    courses_with_both_visibility = CourseOverview.objects.filter(catalog_visibility="both").values("id")
    orgs = [[x.id, x.name] for x in MainCourseClassification.objects.filter(
        is_active=True,
        visibility__in=[1, 2],
        id__in=CourseClassification.objects.filter(course_id__in = courses_with_both_visibility).values_list('MainClass', flat=True).distinct()
    ).order_by('sequence')]
    return orgs

def get_all_course_categories():
    """
        Return all active course categories that have courses
    """
    courses_with_both_visibility = CourseOverview.objects.filter(catalog_visibility="both").values("id")
    orgs = [[x.id, x.name] for x in CourseCategory.objects.filter(
        show_opt__in=[1, 2],
        courseclassification__isnull=False,
        courseclassification__course_id__in = courses_with_both_visibility
    ).distinct().order_by('sequence')]
    return orgs

def get_courses_by_category(category_id):
    """
        Return list of courses ids by course category
    """
    courses = list(CourseClassification.objects.filter(course_category__id=category_id).values('course_id'))
    course_ids = [x['course_id'] for x in courses]
    return course_ids

def get_courses_by_classification(org_id):
    """
        Return list of courses by main classification
    """
    courses = list(CourseClassification.objects.filter(MainClass__id=org_id, MainClass__is_active=True).values('course_id'))
    course_ids = [x['course_id'] for x in courses]
    return course_ids

def convert_number(x):
    """
        Return a clean number without '$' symbol or none
    """
    if isinstance(x, (int, float)):
        return float(x)
    try:
        # remove $, commas, and spaces
        cleaned = str(x).replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except ValueError:
        return None  # discard if it cannot be converted

def price_filter(min_price, max_price, input_price):
    """
        Return if a course should be append depending on filter price
    """
    if (min_price != "") and max_price != "":
        if(input_price >= min_price and input_price <= max_price):
            return True
    elif (min_price != ""):
        if(input_price >= min_price):
            return True
    elif (max_price != ""):
        if (input_price <= max_price):
            return True
    else:
        return True
     
def set_data_courses(courses, sort, min_price, max_price, only_free):
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
    today = timezone.now()
    new_courses_data = []
    for course in courses:
        try:
            course_aux = get_course_by_id(CourseKey.from_string(course['_id']))
            course_price = get_cosmetic_display_price(course_aux)
            new_course = course["data"]
            course_start = new_course.get("start",None)
            new_course['extra_data'] = {
                'effort' : new_course.get("effort", None),
                'self_paced' : course_aux.self_paced,
                'invitation_only' : course_aux.invitation_only,
                'price' : course_price
            }
            new_course['time_left'] = set_time_left(datetime.fromisoformat(course_start), today)
            new_course['course_state']= set_course_state(new_course, today)
            if only_free:
                if course_price == 'Free' or course_price == 'Gratis' or course_price == None:
                    new_courses_data.append(new_course)
            else:
                input_price = convert_number(course_price)
                if(price_filter(min_price, max_price, input_price)):
                    new_courses_data.append(new_course)
        except Exception as e:
            error = f'Course Discovery - Error in course_classification set_data_courses function course not found, error: {format(str(e))}'
            log.error(error)
    new_courses_data =  sorted(new_courses_data, key=lambda course: sort_by_state_and_start_date(course, sort)) 
    return new_courses_data
def set_course_state(course, today):
    """
    Set course state to a course, using today date and resulting in one of this states:
    upcoming_enrollable, upcoming_notenrollable, ongoing_notenrollable, ongoing_enrollable, completed and other as default state
    """
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
    # If the course enrollment is by invitation
    if is_invitation_only:
        # If course hasn't started yet
        if course_start > today:
            return 'upcoming_notenrollable'
        # If course hasn't ended and already start
        elif course_end is None or course_end > today:
            return 'ongoing_notenrollable'
        # If course already end
        else:
            return 'completed'
    # If today is between enrollment range and the course already started 
    elif enroll_start <= today and (enroll_end > today) and course_start <= today and (course_end is None or course_end > today):
        return 'ongoing_enrollable'
    # If you are not within the registration deadline today and the course has already begun
    elif enroll_start < today and (enroll_end < today) and course_start <= today and (course_end is None or course_end > today):
        return 'ongoing_notenrollable'
    # If you are not within the registration deadline today and the course has not yet started
    elif enroll_start < today and (enroll_end < today) and course_start > today and (course_end is None or course_end > today):
        return 'upcoming_notenrollable'
    # If you are within the enrollment range today and the course has not yet started
    elif enroll_start <= today and (enroll_end > today) and course_start > today:
        return 'upcoming_enrollable'
    # If you are not within the enrollment range today and the course has not yet started
    elif enroll_start > today and (enroll_end > today) and course_start > today:
        return 'upcoming_notenrollable'
    # If today is after the end date of the course
    elif course_end is not None and course_end <= today:
        return 'completed'     
    else:
        return 'other'
   
def sort_by_state_and_start_date(course, sort):
    """
    Classify and sort courses based on their state and start date using a dictionary.
    """
    state_order_dict = ['ongoing_enrollable', 'upcoming_enrollable', 'upcoming_notenrollable','ongoing_notenrollable','completed','other']
    map_order = {state: index for index, state in enumerate(state_order_dict)}
    state_order = map_order[course['course_state']]
    date_start = datetime.fromisoformat(course['start']).timestamp()
    if sort=='start':
        return (state_order, date_start)
    else:
        return (state_order, -date_start)

