# -*- coding:utf-8 -*-
import os
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from model_utils import Choices
from django.core.exceptions import ValidationError
from opaque_keys.edx.django.models import CourseKeyField
from django.utils.translation import ugettext_lazy as _

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

def template_assets_path(instance, filename):
    """
    Delete the file if it already exist and returns the certificate template asset file path.

    :param instance: MainCourseClassification object
    :param filename: file to upload
    :return path: path of asset file e.g. course_classification_assets/1/filename
    """
    name = os.path.join('course_classification_assets', str(instance.id), filename)
    fullname = os.path.join(settings.MEDIA_ROOT, name)
    if os.path.exists(fullname):
        os.remove(fullname)
    return name

class MainCourseClassification(models.Model):
    OPTIONS = Choices((0,'index',('Portada')),(1,'search',('Buscador')),(2,'both',('Ambos')))
    name = models.CharField(max_length=255,verbose_name=_('name'),unique=True)
    banner = models.FileField(
        max_length=255,
        upload_to=template_assets_path,
        help_text=_(u'Banner file. 500 px height'),
        blank=True
    )
    logo = models.FileField(
        max_length=255,
        upload_to=template_assets_path,
        help_text=_(u'Logo file. 145 px height'),
        blank=True
    )
    sequence = models.IntegerField(verbose_name=_('sequence'))
    is_active = models.BooleanField(default=True, help_text=_(u'Show: True, Hide: False'))
    visibility = models.IntegerField(choices=OPTIONS,default=2,verbose_name=_('Mostrar en'))

    def save(self, *args, **kwargs):
        """save the course classification asset """
        if self.pk is None:
            banner_image = self.banner
            self.banner = None
            logo_image = self.logo
            self.logo = None
            super(MainCourseClassification, self).save(*args, **kwargs)
            self.banner = banner_image
            self.logo = logo_image

        super(MainCourseClassification, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta(object):
        ordering = ('sequence','name',)

class CourseCategory(models.Model):
    SHOW_OPT = Choices((0,'no_show',('No Mostrar')),(1,'only_with_course',('Solo si tiene cursos')),(2,'always',('Siempre')))
    name = models.CharField(max_length=255,verbose_name=_('name'),unique=True)
    sequence = models.IntegerField(verbose_name=_('sequence'))
    show_opt = models.IntegerField(choices=SHOW_OPT,default=0,verbose_name=_('Mostrar'))

    def __str__(self):
        return self.name
    class Meta(object):
        ordering = ('sequence','name',)

class MainCourseClassificationTemplate(models.Model):
    class Meta:
        index_together = [
            ["main_classification", "language"],
        ]
        unique_together = [
            ["main_classification", "language"],
        ]

    main_classification = models.ForeignKey(
        MainCourseClassification,
        on_delete=models.CASCADE,
        related_name="main_classification")

    template = models.TextField(
        help_text=_(u'Django template HTML.'),
    )
    language = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        help_text=u'es_419 or en'
    )
    def __str__(self):
        return '{} - {}'.format(self.main_classification.name, self.language)

class CourseClassification(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True, unique=True,verbose_name=_('course'))
    MainClass = models.ForeignKey(MainCourseClassification,verbose_name='Clasificación Principal', on_delete=models.CASCADE, blank=True, null=True)
    course_category = models.ManyToManyField(CourseCategory,verbose_name='Categorias', blank=True)
    
    class Meta(object):
        ordering = ('course_id',)
