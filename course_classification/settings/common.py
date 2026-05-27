def plugin_settings(settings):
    settings.EXPLORE_COURSES_PAGE_SIZE = 20
    settings.MAX_ELASTICSEARCH_PAGE_SIZE = 200
    settings.COURSE_SEARCH_INITIAL_YEAR = 2020
    settings.COURSE_SEARCH_FUTURE_TIME_HORIZON = 262080 #approx 6 month
    