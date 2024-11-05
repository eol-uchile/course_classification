#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock, MagicMock
from collections import namedtuple
from django.urls import reverse
from django.test import TestCase, Client
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from urllib.parse import parse_qs
import urllib.parse
from opaque_keys.edx.locator import CourseLocator
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.student.tests.factories import CourseEnrollmentAllowedFactory, UserFactory, CourseEnrollmentFactory
import json
from . import helpers
from .views import CourseClassificationView
from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime
  
class TestCourseClassification(ModuleStoreTestCase):
    def setUp(self):
        super(TestCourseClassification, self).setUp()
        self.course = CourseFactory.create(
            org='mss',
            course='999',
            display_name='2020',
            catalog_visibility="both",
            emit_signals=True,
            start_date=datetime(2023, 1, 1))
        aux = CourseOverview.get_from_id(self.course.id)
        self.course2 = CourseFactory.create(
            org='mss',
            course='222',
            display_name='2021',
            catalog_visibility="both",
            emit_signals=True,
            start_date=datetime(2023, 2, 1))
        aux = CourseOverview.get_from_id(self.course2.id)
        self.course3 = CourseFactory.create(
            org='mss',
            course='333',
            display_name='2021',
            catalog_visibility="none",
            emit_signals=True,
            start_date=datetime(2023, 5, 1))
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
        response = helpers.set_data_courses([{'_id':str(self.course.id)},{'_id':str(self.course2.id)},{'_id':str(self.course3.id)}])
        expected = [
            {'_id':str(self.course.id), 'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'main_classification':{
                                                'name':mcc1.name, 
                                                'logo':mcc1.logo.url 
                                            }
                                        }
                                    },
            {'_id':str(self.course2.id), 'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'main_classification':{
                                                'name':mcc2.name, 
                                                'logo':''
                                            }
                                        }
                                    },
            {'_id':str(self.course3.id), 'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'main_classification':{}
                                        }
                                    },
            ]
        self.assertEqual(response, expected)

    def test_set_data_courses_no_courses(self):
        """
            test set data courses when course id from elasticsearch doesnt exists in course overviews
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
        response = helpers.set_data_courses([{'_id':str(self.course.id)},{'_id':'course-v1:eol+Test+2023'},])
        expected = [
            {'_id':str(self.course.id), 'extra_data':{
                                            'short_description' : None, 
                                            'advertised_start' : None, 
                                            'display_org_with_default' : 'mss',
                                            'main_classification':{
                                                'name':mcc1.name, 
                                                'logo':mcc1.logo.url 
                                            }
                                        }
                                    },
            {'_id':'course-v1:eol+Test+2023', 'extra_data':{'main_classification':{}}},
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
