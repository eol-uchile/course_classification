# Installed packages (via pip)
from django.conf.urls import url

# Internal project dependencies
from .views import CourseClassificationView, course_discovery_eol, get_course_categories_view, get_main_classifications_view, get_initial_settings


urlpatterns = (
    url(
        r'^institutions/(?P<org_id>\d+)/',
        CourseClassificationView.as_view(),
        name='institution',
    ),
    url(r'^course_classification/search/$', course_discovery_eol, name='course_discovery_eol'),
    url(r'^course_classification/get_main_classifications/', get_main_classifications_view, name='get_all_main_classifications'),
    url(r'^course_classification/get_course_categories/', get_course_categories_view, name='get_all_course_categories'),
    url(r'^course_classification/get_initial_settings/', get_initial_settings, name='get_initial_date_settings'),
)
