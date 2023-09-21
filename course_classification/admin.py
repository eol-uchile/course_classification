# -*- coding:utf-8 -*-
from django.contrib import admin
from django import forms
from xmodule.modulestore.django import modulestore
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from django.core.exceptions import ValidationError
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from django.core.validators import URLValidator

from .models import MainCourseClassification, CourseClassification, MainCourseClassificationTemplate, CourseCategory

class MainCourseClassificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'sequence', 'is_active',)
    search_fields = ['name', 'sequence',]

class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sequence', 'show_opt',)
    search_fields = ['name', 'sequence', 'show_opt',]

class CourseClassificationAdmin(admin.ModelAdmin):
    fields = ('course_id','MainClass', 'course_category',)
    search_fields = ('course_id',)
    list_display = ('course_id','MainClass','categories')
    
    def categories(self, obj):
        return ", ".join([p.name for p in obj.course_category.all()])

class MainCourseClassificationTemplateAdmin(admin.ModelAdmin):
    raw_id_fields = ('main_classification',)
    list_display = ('main_classification', 'language', )
    search_fields = ['main_classification__name', 'language']

admin.site.register(MainCourseClassification, MainCourseClassificationAdmin)
admin.site.register(CourseCategory, CourseCategoryAdmin)
admin.site.register(CourseClassification, CourseClassificationAdmin)
admin.site.register(MainCourseClassificationTemplate, MainCourseClassificationTemplateAdmin)
