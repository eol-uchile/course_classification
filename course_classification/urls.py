from django.conf.urls import url

from .views import CourseClassificationView

urlpatterns = (
    url(
        r'^(?P<org_id>\d+)/',
        CourseClassificationView.as_view(),
        name='institution',
    ),
)
