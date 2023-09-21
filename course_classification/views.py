#!/usr/bin/env python
# -- coding: utf-8 --

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.base import View
from django.http import HttpResponse
from opaque_keys.edx.keys import CourseKey
from opaque_keys import InvalidKeyError
from common.djangoapps.util.json_request import JsonResponse, JsonResponseBadRequest
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate
import json
import requests
import logging

logger = logging.getLogger(__name__)

class CourseClassificationView(View):
    """
        Page view for institutions (MainCourseClassification)
    """
    def get(self, request, org_id):
        try:
            classification = MainCourseClassification.objects.get(id=org_id, is_active=True)
            if classification.banner == "":
                logger.info("CourseClassificationView - Classification dont have banner, MainCourseClassification id: {}".format(org_id))
                return HttpResponseRedirect('/')
            course_ids = [x.course_id for x in CourseClassification.objects.filter(MainClass=classification)]
            if MainCourseClassificationTemplate.objects.filter(main_classification=classification, language="es_419").exists():
                template = MainCourseClassificationTemplate.objects.get(main_classification=classification, language="es_419")
            elif MainCourseClassificationTemplate.objects.filter(main_classification=classification, language="en").exists():
                template = MainCourseClassificationTemplate.objects.get(main_classification=classification, language="en")
            else:
                logger.info("CourseClassificationView - Classification dont have es_419 or en template, MainCourseClassification id: {}".format(org_id))
                return HttpResponseRedirect('/')
            context = {
                'institution_name': classification.name,
                'institution_banner': classification.banner.url,
                'institution_html': template.template,
                'courses': CourseOverview.objects.filter(id__in=course_ids)
            }
            return render(request, 'course_classification/institution.html', context)
        except Exception as e:
            logger.info("CourseClassificationView - Active classification does not exists, id: {}, error: {}".format(org_id, str(e)))
            return HttpResponseRedirect('/')
