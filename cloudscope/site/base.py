# cloudscope.site.base
# Manages the rendering of Jinja2 templates to the deploy folder.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Sun Jan 10 08:13:39 2016 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: base.py [] benjamin@bengfort.com $

"""
Manages the rendering of Jinja2 templates to the deploy folder.
"""

##########################################################################
## Imports
##########################################################################

import os

from jinja2 import Environment, PackageLoader

from cloudscope.config import settings
from cloudscope.exceptions import ImproperlyConfigured


##########################################################################
## Helper Functions
##########################################################################

def get_site_context(**kwargs):
    """
    Returns the site context from the YAML configuration.
    """
    context = {
        'debug': settings.debug,
        'testing': settings.testing,
        'site': dict(settings.site.options())
    }

    context.update(kwargs)
    return context


##########################################################################
## Page Object
##########################################################################

class Page(object):
    """
    Base class that wraps an HTML page and provides context.
    """

    page_url_path = None
    template_name = None

    def __init__(self, **kwargs):
        # Pop any required properties from kwargs
        self._environment  = kwargs.pop('environment', None)
        self.template_name = kwargs.pop('template_name', Page.template_name)
        self.page_url_path = kwargs.pop('page_url_path', Page.page_url_path)

        # Set the remaining properties as extra context
        self.extra = kwargs

    @property
    def environment(self):
        """
        The Jinja2 environment and template loader
        """
        if self._environment is None:
            loader = PackageLoader('cloudscope.site', 'templates')
            self._environment = Environment(loader=loader)
        return self._environment

    def get_template(self):
        """
        Uses Jinja2 to fetch the template from the environment
        """
        if self.template_name is None:
            raise ImproperlyConfigured(
                "Pages requires either a definition of template_name "
                "or an implementation of get_template on the subclass."
            )
        return self.environment.get_template(self.template_name)

    def get_url_path(self):
        """
        Returns the file path to render the page to based on the static
        location and the page_url_path property set on the class.
        """
        if self.page_url_path is None:
            raise ImproperlyConfigured(
                "Pages requires either a definition of page_url_path "
                "or an implementation of get_url_path on the subclass."
            )

        path = self.page_url_path

        # Create index.html files for pretty urls
        if path.endswith('/'):
            path += "index.html"

        return os.path.join(settings.site.htdocs, path)

    def get_context_data(self, **kwargs):
        """
        Gets the global site context and returns any extra configuration.
        """
        context = self.extra.copy()
        context.update(kwargs)
        return get_site_context(**context)

    def render(self, **kwargs):
        """
        Renders the page with the template and context data to it's path.
        """
        path     = self.get_url_path()
        template = self.get_template()
        context  = self.get_context_data(**kwargs)

        print path

        # Create any needed directories along the path
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        print dirname
        print path

        # Stream the template rendering to the file.
        template.stream(context).dump(path, encoding='utf-8')


if __name__ == '__main__':
    page = Page(template_name='page.html', page_url_path='about/')
    page.render(page={'title': 'About', 'description': 'About Us'})
