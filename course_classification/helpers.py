# -*- coding:utf-8 -*-
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory
from django.db.models import Q
from django.urls import reverse

def get_course_ctgs(courses):
    """
        Return dict with categories and its courses
    """
    ret_courses = {}
    for main in CourseCategory.objects.all():
        ret_courses[main.id] = {'id':main.id,'name':main.name, 'seq':main.sequence,'show_opt':main.show_opt, 'courses':[]}
    for course in courses:
        try:
            course_class = CourseClassification.objects.get(course_id=course.pk)
            for ctg in course_class.course_category.all():
                ret_courses[ctg.id]['courses'].append(course)
        except CourseClassification.DoesNotExist:
            pass
    return ret_courses

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