import setuptools

setuptools.setup(
    name="course_classification",
    version="0.0.1",
    author="Luis Santana",
    author_email="luis.santana@uchile.cl",
    description=".",
    url="https://eol.uchile.cl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "lms.djangoapp": ["course_classification = course_classification.apps:CourseClassificationConfig"],
        "cms.djangoapp": ["course_classification = course_classification.apps:CourseClassificationConfig"]
    },
)
