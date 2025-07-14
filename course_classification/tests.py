#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python Standard Libraries
from datetime import datetime
import copy
import json
import urllib.parse

# Installed packages (via pip)
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseRedirect
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from elasticsearch import Elasticsearch
from mock import patch, MagicMock
from search.api import NoSearchEngineError
from search.elastic import ElasticSearchEngine
from search.tests.utils import SearcherMixin, TEST_INDEX_NAME

# Edx dependencies
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

# Internal project dependencies
from . import helpers
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory
from .views import CourseClassificationView, course_discovery_eol
from .api import course_discovery_search_eol
class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None
    COOKIES = {}
    POST = {}

class TestCourseClassification(ModuleStoreTestCase):
    def setUp(self):
        super(TestCourseClassification, self).setUp()
        self.course = CourseFactory.create(
            org='mss',
            course='999',
            display_name='2020',
            catalog_visibility="both",
            emit_signals=True,
            start_date='2023-03-01T00:00:00+00:00')
        aux = CourseOverview.get_from_id(self.course.id)
        self.course2 = CourseFactory.create(
            org='mss',
            course='222',
            display_name='2021',
            catalog_visibility="both",
            emit_signals=True,
            start_date='2023-02-01T00:00:00+00:00')
        aux = CourseOverview.get_from_id(self.course2.id)
        self.course3 = CourseFactory.create(
            org='mss',
            course='333',
            display_name='2021',
            catalog_visibility="none",
            emit_signals=True,
            start_date='2023-05-01T00:00:00+00:00')
        aux = CourseOverview.get_from_id(self.course3.id)
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client = Client()
            self.user_staff = UserFactory(
                username='testuser3',
                password='12345',
                email='student2@edx.org',
                is_staff=True)
            self.client.login(username='testuser3', password='12345')

            # user student
            self.student_client = Client()
            self.student = UserFactory(
                username='student',
                password='12345',
                email='student@edx.org')
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course2.id)
            self.assertTrue(
                self.student_client.login(
                    username='student',
                    password='12345'))

    def test_helpers_get_course_ctgs(self):
        """
            Test get_course_ctgs() normal process
        """
        cctg1 = CourseCategory.objects.create(name="T1", sequence=1, show_opt=2)
        cctg2 = CourseCategory.objects.create(name="T2", sequence=2, show_opt=2)
        cc = CourseClassification.objects.create(course_id=self.course.id)
        cc.save()
        cc.course_category.add(cctg1)
        cc.course_category.add(cctg2)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id)
        cc2.save()
        cc2.course_category.add(cctg2)
        cc2.save()
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course2, self.course3])
        expected = {
            cctg1.id: {'id':cctg1.id,'name':cctg1.name, 'seq':cctg1.sequence,'show_opt':cctg1.show_opt, 'courses':[self.course]},
            cctg2.id: {'id':cctg2.id,'name':cctg2.name, 'seq':cctg2.sequence,'show_opt':cctg2.show_opt, 'courses':[self.course, self.course2]},
            }
        self.assertEqual(len(response), 2)
        self.assertEqual(len(mc_courses), 0)
        self.assertEqual(response[cctg1.id]['id'], expected[cctg1.id]['id'])
        self.assertEqual(response[cctg1.id]['name'], expected[cctg1.id]['name'])
        self.assertEqual(response[cctg1.id]['show_opt'], expected[cctg1.id]['show_opt'])
        self.assertEqual(response[cctg1.id]['courses'], expected[cctg1.id]['courses'])
        self.assertEqual(response[cctg2.id]['id'], expected[cctg2.id]['id'])
        self.assertEqual(response[cctg2.id]['name'], expected[cctg2.id]['name'])
        self.assertEqual(response[cctg2.id]['show_opt'], expected[cctg2.id]['show_opt'])
        self.assertEqual(response[cctg2.id]['courses'], expected[cctg2.id]['courses'])

    def test_helpers_get_course_ctgs_featured(self):
        """
            Test get_course_ctgs() normal process with featured courses
        """
        cctg1 = CourseCategory.objects.create(name="T1", sequence=1, show_opt=2)
        cctg2 = CourseCategory.objects.create(name="T2", sequence=2, show_opt=2)
        cc = CourseClassification.objects.create(course_id=self.course.id)
        cc.save()
        cc.course_category.add(cctg1)
        cc.course_category.add(cctg2)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, is_featured_course=True)
        cc2.save()
        cc2.course_category.add(cctg2)
        cc2.save()
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course2, self.course3])
        expected = {
            'featured': [self.course2],
            }
        self.assertEqual(len(response), 1)
        self.assertEqual(len(mc_courses), 0)
        self.assertEqual(response, expected)

    def test_helpers_get_course_ctgs_featured_no_courses(self):
        """
            Test get_course_ctgs() normal process with featured courses created but not in catalog
        """
        cctg1 = CourseCategory.objects.create(name="T1", sequence=1, show_opt=2)
        cctg2 = CourseCategory.objects.create(name="T2", sequence=2, show_opt=2)
        cc = CourseClassification.objects.create(course_id=self.course.id)
        cc.save()
        cc.course_category.add(cctg1)
        cc.course_category.add(cctg2)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, is_featured_course=True)
        cc2.save()
        cc2.course_category.add(cctg2)
        cc2.save()
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course3])
        expected = {
            cctg1.id: {'id':cctg1.id,'name':cctg1.name, 'seq':cctg1.sequence,'show_opt':cctg1.show_opt, 'courses':[self.course]},
            cctg2.id: {'id':cctg2.id,'name':cctg2.name, 'seq':cctg2.sequence,'show_opt':cctg2.show_opt, 'courses':[self.course]},
            }
        self.assertEqual(len(response), 2)
        self.assertEqual(len(mc_courses), 0)
        self.assertEqual(response[cctg1.id]['id'], expected[cctg1.id]['id'])
        self.assertEqual(response[cctg1.id]['name'], expected[cctg1.id]['name'])
        self.assertEqual(response[cctg1.id]['show_opt'], expected[cctg1.id]['show_opt'])
        self.assertEqual(response[cctg1.id]['courses'], expected[cctg1.id]['courses'])
        self.assertEqual(response[cctg2.id]['id'], expected[cctg2.id]['id'])
        self.assertEqual(response[cctg2.id]['name'], expected[cctg2.id]['name'])
        self.assertEqual(response[cctg2.id]['show_opt'], expected[cctg2.id]['show_opt'])
        self.assertEqual(response[cctg2.id]['courses'], expected[cctg2.id]['courses'])

    def test_helpers_get_course_ctgs_no_courses(self):
        """
            Test get_course_ctgs() without courses configured
        """
        cctg1 = CourseCategory.objects.create(name="T1", sequence=1, show_opt=2)
        cctg2 = CourseCategory.objects.create(name="T2", sequence=2, show_opt=2)
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course2, self.course3])
        expected = {
            cctg1.id: {'id':cctg1.id,'name':cctg1.name, 'seq':cctg1.sequence,'show_opt':cctg1.show_opt, 'courses':[]},
            cctg2.id: {'id':cctg2.id,'name':cctg2.name, 'seq':cctg2.sequence,'show_opt':cctg2.show_opt, 'courses':[]},
            }
        self.assertEqual(len(response), 2)
        self.assertEqual(len(mc_courses), 0)
        self.assertEqual(response[cctg1.id]['id'], expected[cctg1.id]['id'])
        self.assertEqual(response[cctg1.id]['name'], expected[cctg1.id]['name'])
        self.assertEqual(response[cctg1.id]['show_opt'], expected[cctg1.id]['show_opt'])
        self.assertEqual(response[cctg1.id]['courses'], expected[cctg1.id]['courses'])
        self.assertEqual(response[cctg2.id]['id'], expected[cctg2.id]['id'])
        self.assertEqual(response[cctg2.id]['name'], expected[cctg2.id]['name'])
        self.assertEqual(response[cctg2.id]['show_opt'], expected[cctg2.id]['show_opt'])
        self.assertEqual(response[cctg2.id]['courses'], expected[cctg2.id]['courses'])

    def test_helpers_get_course_ctgs_no_categories(self):
        """
            Test get_course_ctgs() without categories configured
        """
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course2, self.course3])
        expected = {}
        self.assertEqual(len(response), 0)
        self.assertEqual(len(mc_courses), 0)

    def test_helpers_get_course_course_wo_ctgs(self):
        """
            Test get_course_ctgs() when courses doesnt have cateogories
        """
        cc = CourseClassification.objects.create(course_id=self.course.id)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id)
        cc2.save()
        response, mc_courses = helpers.get_course_ctgs([self.course, self.course2, self.course3])
        expected = {}
        self.assertEqual(len(response), 0)
        self.assertEqual(len(mc_courses), 0)

    def test_helpers_get_all_logos(self):
        """
            Test get_all_logos() normal process
        """
        MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            ).save()
        MainCourseClassification(
            name="MCC2",
            sequence=2,
            visibility=2,
            is_active=True
            ).save()
        MainCourseClassification(
            name="MCC3",
            logo=SimpleUploadedFile(
                "test3.png",
                b"test3" 
            ),
            sequence=3,
            visibility=2,
            is_active=False
            ).save()
        MainCourseClassification(
            name="MCC4",
            logo=SimpleUploadedFile(
                "test4.png",
                b"test4" 
            ),
            sequence=4,
            visibility=1,
            is_active=True
            ).save()
        expected = [["/static/uploads/course_classification_assets/1/test.png", None]]
        response = helpers.get_all_logos()
        self.assertEqual(len(response), 1)
        self.assertEqual(response, expected)
    
    def test_helpers_get_all_logos_with_templates(self):
        """
            Test get_all_logos() normal process with template
        """
        MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            ).save()
        MainCourseClassificationTemplate(
            main_classification=MainCourseClassification.objects.get(name="MCC1"),
            template="hello world",
            language="en"
        ).save()
        expected = [["/static/uploads/course_classification_assets/1/test.png", reverse('course_classification:institution', kwargs={'org_id':1})]]
        response = helpers.get_all_logos()
        self.assertEqual(len(response), 1)
        self.assertEqual(response, expected)

    def test_helpers_get_all_main_classifications(self):
        """
            Test get_all_main_classifications() normal process
        """
        response = helpers.get_all_main_classifications()
        self.assertEqual(len(response), 0)
        MainCourseClassification(
            name="MCC1",
            sequence=2,
            visibility=2,
            is_active=True
            ).save()
        MainCourseClassification(
            name="MCC2",
            sequence=1,
            visibility=1,
            is_active=True
            ).save()
        MainCourseClassification(
            name="MCC3",
            sequence=3,
            visibility=2,
            is_active=False
            ).save()
        MainCourseClassification(
            name="MCC4",
            sequence=4,
            visibility=0,
            is_active=True
            ).save()
        expected = [[2, "MCC2"],[1, "MCC1"]]
        response = helpers.get_all_main_classifications()
        self.assertEqual(len(response), 2)
        self.assertEqual(response, expected)
    
    def test_helpers_get_courses_by_classification(self):
        """
            Test get_courses_by_classification() normal process
        """
        mcc1 = MainCourseClassification(
            name="MCC1",
            sequence=2,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        mcc2 = MainCourseClassification(
            name="MCC2",
            sequence=1,
            visibility=1,
            is_active=False
            )
        mcc2.save()
        cc = CourseClassification.objects.create(course_id=self.course.id, MainClass=mcc1)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, MainClass=mcc2)
        cc2.save()

        response = helpers.get_courses_by_classification(mcc1.id)
        self.assertEqual(response, [self.course.id])

        response = helpers.get_courses_by_classification(mcc2.id)
        self.assertEqual(response, [])

        response = helpers.get_courses_by_classification(999)
        self.assertEqual(response, [])
    
    def test_get_featured_courses(self):
        """
            test get_featured_courses() normal process
        """
        mcc1 = MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        cc = CourseClassification.objects.create(course_id=self.course.id, MainClass=mcc1, is_featured_course=True)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, MainClass=mcc1, is_featured_course=False)
        cc2.save()
        expected = {
            'name': mcc1.name,
            'logo': mcc1.logo
        }
        response, mc_courses = helpers.get_featured_courses()
        self.assertEqual(len(response), 1)
        self.assertEqual(list(response)[0].id, self.course.id)
        self.assertEqual(len(mc_courses), 1)
        self.assertEqual(mc_courses[self.course.id], expected)

    def test_get_featured_courses_no_courses(self):
        """
            test get_featured_courses when featured coures is empty
        """
        mcc1 = MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        cc = CourseClassification.objects.create(course_id=self.course.id, MainClass=mcc1, is_featured_course=False)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, MainClass=mcc1, is_featured_course=False)
        cc2.save()
        response, mc_courses = helpers.get_featured_courses()
        self.assertEqual(len(response), 0)
        self.assertEqual(len(mc_courses), 0)

    def test_set_data_courses(self):
        """
            test set data course normal process
        """
        mcc1 = MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=2,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        mcc2 = MainCourseClassification(
            name="MCC2",
            sequence=1,
            visibility=1,
            is_active=False
            )
        mcc2.save()
        cc = CourseClassification.objects.create(course_id=self.course.id, MainClass=mcc1)
        cc.save()
        cc2 = CourseClassification.objects.create(course_id=self.course2.id, MainClass=mcc2)
        cc2.save()
        today = timezone.now()
        response = helpers.set_data_courses([{'_id':str(self.course.id),'data': {
                        'id': str(self.course.id),
                        'start': str(self.course.start_date)
                    }},{'_id':str(self.course2.id),'data': {
                        'id': str(self.course2.id),
                        'start': str(self.course2.start_date)
                    }},{'_id':str(self.course3.id),'data': {
                        'id': str(self.course3.id),
                        'start': str(self.course3.start_date)
                    }}])
        expected = [
            {'id':str(self.course.id), 'start': str(self.course.start_date),
             'time_left':helpers.set_time_left(datetime.fromisoformat(str(self.course.start_date)), today),
             'course_state': 'ongoing_enrollable',
             'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'invitation_only': False,
                                            'main_classification':{
                                                'name':mcc1.name, 
                                                'logo':mcc1.logo.url 
                                            }
                                        }
                                    },
            {'id':str(self.course2.id), 'start': str(self.course2.start_date),
             'time_left':helpers.set_time_left(datetime.fromisoformat(str(self.course2.start_date)), today),
             'course_state': 'ongoing_enrollable',
             'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'invitation_only': False,
                                            'main_classification':{
                                                'name':mcc2.name, 
                                                'logo':''
                                            }
                                        }
                                    },
            {'id':str(self.course3.id),'start': str(self.course3.start_date), 
             'time_left':helpers.set_time_left(datetime.fromisoformat(str(self.course3.start_date)), today),
             'course_state': 'ongoing_enrollable',
             'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'invitation_only': False,
                                            'main_classification':{}
                                        }
                                    },
            ]
        self.assertEqual(response, expected)

    def test_set_data_courses_no_courses(self):
        """
            test set data courses when course id from elasticsearch doesn't exists in course overviews
        """
        mcc1 = MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=2,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        cc = CourseClassification.objects.create(course_id=self.course.id, MainClass=mcc1)
        cc.save()
        response = helpers.set_data_courses([{'_id':str(self.course.id),'data': {
                        'id': str(self.course.id),
                        'start':  str(self.course.start_date)
                    }},{'_id':'course-v1:eol+Test+2023','data': {
                        'id':'course-v1:eol+Test+2023','start':  str(self.course.start_date)}
                        },])
        today = timezone.now()
        expected = [
            {'id':str(self.course.id),'start':  str(self.course.start_date),
            'time_left':helpers.set_time_left(datetime.fromisoformat(str(self.course.start_date)), today),
            'course_state': 'ongoing_enrollable',
            'extra_data':{
                'short_description' : None, 
                'advertised_start' : None, 
                'display_org_with_default' : 'mss',
                'invitation_only': False,
                'main_classification':{
                    'name':mcc1.name, 
                    'logo':mcc1.logo.url 
                }
            }},
            {'id':'course-v1:eol+Test+2023','start':  str(self.course.start_date),
            'time_left':helpers.set_time_left(datetime.fromisoformat(str(self.course.start_date)), today),
            'course_state': 'ongoing_enrollable',
            'extra_data':{'main_classification':{}}},
            ]
        self.assertEqual(response, expected)

    def test_view(self):
        """
            Test institution page
        """
        # main classification does not exists
        self.client.cookies.load({'openedx-language-preference': "en"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':999}))
        request = urllib.parse.urlparse(result.url)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(request.path, '/')
        # main classification exists
        mcc1 = MainCourseClassification(
            name="MCC1",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            )
        mcc1.save()
        MainCourseClassificationTemplate(
            main_classification=mcc1,
            template="hello world",
            language="en"
        ).save()
        MainCourseClassificationTemplate(
            main_classification=mcc1,
            template="hola mundo",
            language="es_419"
        ).save()
        self.client.cookies.load({'openedx-language-preference': "en"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':mcc1.id}))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.request['PATH_INFO'], '/institutions/1/')
        self.assertTrue('hello world' in result._container[0].decode())

        self.client.cookies.load({'openedx-language-preference': "es-419"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':mcc1.id}))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.request['PATH_INFO'], '/institutions/1/')
        self.assertTrue('hola mundo' in result._container[0].decode())

        # main classification does not have language template
        self.client.cookies.load({'openedx-language-preference': "fr"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':mcc1.id}))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.request['PATH_INFO'], '/institutions/1/')
        self.assertTrue('hello world' in result._container[0].decode())
        
        # main classification does not have template
        mcc2 = MainCourseClassification(
            name="MCC2",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=True
            )
        mcc2.save()
        self.client.cookies.load({'openedx-language-preference': "en"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':mcc2.id}))
        request = urllib.parse.urlparse(result.url)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(request.path, '/')
        # main classification is_active=False
        mcc3 = MainCourseClassification(
            name="MCC3",
            logo=SimpleUploadedFile(
                "test.png",
                b"test" 
            ),
            banner=SimpleUploadedFile(
                "banner.png",
                b"banner" 
            ),
            sequence=1,
            visibility=2,
            is_active=False
            )
        mcc3.save()
        MainCourseClassificationTemplate(
            main_classification=mcc3,
            template="hello world",
            language="en"
        ).save()
        self.client.cookies.load({'openedx-language-preference': "en"})
        result = self.client.get(reverse('course_classification:institution', kwargs={'org_id':mcc3.id}))
        request = urllib.parse.urlparse(result.url)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(request.path, '/')

    def test_redirect_when_banner_empty(self):
        """ Check if redirect properly when banner is empty"""
        mock_classification = MagicMock()
        mock_classification.banner = ""
        with patch('course_classification.views.MainCourseClassification') as mock_classification_model:
            mock_classification_model.objects.get.return_value = mock_classification
            request = TestRequest()
            request.method = 'POST'
            request.COOKIES['openedx-language-preference'] = 'en'
            response = CourseClassificationView().get(request, org_id=1)
            self.assertIsInstance(response, HttpResponseRedirect)
            self.assertEqual(response.url, '/')

class DemoCourse:
    """ Class for dispensing demo courses """
    DEMO_COURSE_ID = "edX/DemoX/Demo_Course"
    DEMO_COURSE = {
        "start": datetime(2014, 2, 1),
        "number": "DemoX",
        "content": {
            "short_description": "Short description",
            "overview": "Long overview page",
            "display_name": "edX Demonstration Course",
            "number": "DemoX"
        },
        "course": "edX/DemoX/Demo_Course",
        "image_url": "/c4x/edX/DemoX/asset/images_course_image.jpg",
        "effort": "5:30",
        "id": DEMO_COURSE_ID,
        "enrollment_start": datetime(2014, 1, 1),
    }

    demo_course_count = 0

    @classmethod
    def get(cls, update_dict=None, remove_fields=None):
        """ get a new demo course """
        cls.demo_course_count += 1
        course_copy = copy.deepcopy(cls.DEMO_COURSE)
        if update_dict:
            if "content" in update_dict:
                course_copy["content"].update(update_dict["content"])
                del update_dict["content"]
            course_copy.update(update_dict)
        course_copy.update({"id": "{}_{}".format(course_copy["id"], cls.demo_course_count)})
        if remove_fields:
            for remove_field in remove_fields:
                if remove_field in course_copy:
                    del course_copy[remove_field]
        return course_copy

    @classmethod
    def reset_count(cls):
        """ go back to zero """
        cls.demo_course_count = 0

    @staticmethod
    def index(searcher, course_info):
        """ Adds course info dictionary to the index """
        searcher.index(doc_type="course_info", sources=course_info)

    @classmethod
    def get_and_index(cls, searcher, update_dict=None, remove_fields=None):
        """ Adds course info dictionary to the index """
        cls.index(searcher, [cls.get(update_dict, remove_fields)])


@override_settings(ELASTIC_FIELD_MAPPINGS={
    "start_date": {"type": "date"},
    "enrollment_start": {"type": "date"},
    "enrollment_end": {"type": "date"}
})
@override_settings(MOCK_SEARCH_BACKING_FILE=None)
@override_settings(COURSEWARE_INDEX_NAME=TEST_INDEX_NAME)
# Any class that inherits from TestCase will cause too-many-public-methods pylint error
class TestMockCourseDiscoverySearch(ModuleStoreTestCase, SearcherMixin):  # pylint: disable=too-many-public-methods
    """
    Tests course discovery activities
    """

    @property
    def _is_elastic(self):
        """ check search engine implementation, to manage cleanup differently """
        return isinstance(self.searcher, ElasticSearchEngine)

    def setUp(self):
        super(TestMockCourseDiscoverySearch, self).setUp()
        DemoCourse.reset_count()
        self._searcher = None
        course = {
            'org':'orgA',
            'course':'999',
            'display_name':'2020',
            'catalog_visibility':"both",
            'emit_signals':True,
            'start':'2023-03-01T00:00:00+00:00'
            }
        DemoCourse.get_and_index(self.searcher, course)
        DemoCourse.get_and_index(self.searcher, {"enrollment_start": None})
        DemoCourse.get_and_index(self.searcher, {"enrollment_start": datetime(2114, 1, 1)})

    def test_course_list(self):
        """ No arguments to course_discovery_search should show all available courses"""
        results = course_discovery_search_eol()
        self.assertEqual(results["total"],3)
    
    def test_searcher_is_none(self):
        """ Check if searcher is None ans it raises an error """
        with patch('search.api.SearchEngine.get_search_engine', return_value=None):
            with self.assertRaises(NoSearchEngineError):
                course_discovery_search_eol()

    def test_course_discovery_eol(self):
        """Check if course_discovery_eol works properly """
        request = TestRequest()
        request.method = 'POST'
        request.POST = {
            'search_string': '',
            'order_by': '',
            'year': '',
            'state': '',
            'classification': '',
            'page_size': '20',
            'page_index': '0'
        }
        response = course_discovery_eol(request)
        response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response["total"],3)
