from setuptools import setup


with open("README.md", "r") as f:
    long_description = f.read()


setup(name="findsrc",
      version="1.0.0",
      author="Weitian Leung",
      author_email="weitianleung@gmail.com",
      description='Search tool for sources',
      long_description_content_type="text/markdown",
      long_description=long_description,
      keywords="find tool source grep",
      platforms="Platform Independent",
      url="https://github.com/timxx/findsrc",
      license="Apache-2.0",
      python_requires='>=3.5',
      py_modules=["findsrc"],
      entry_points={
          "console_scripts": [
              "findsrc=findsrc:main",
          ]
      },
      install_requires=["colorama"],
      classifiers=[
          "Intended Audience :: Developers",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 3",
          "Topic :: Utilities"
      ])
