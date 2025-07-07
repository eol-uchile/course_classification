from django.conf.urls import url

from .views import CourseClassificationView, course_discovery_eol

urlpatterns = (
    url(
        r'^institutions/(?P<org_id>\d+)/',
        CourseClassificationView.as_view(),
        name='institution',
    ),
    url(r'^course_classification/search/$', course_discovery_eol, name='course_discovery_eol'),
)
