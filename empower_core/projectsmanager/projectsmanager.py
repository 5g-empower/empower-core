#!/usr/bin/env python3
#
# Copyright (c) 2019 Roberto Riggio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

"""Projects manager."""

from empower_core.walkmodule import walk_module
from empower_core.launcher import srv_or_die
from empower_core.service import EService
from empower_core.projectsmanager.project import Project
from empower_core.projectsmanager.appcallbackhandler import \
    AppCallbacksHandler
from empower_core.projectsmanager.cataloghandler import CatalogHandler
from empower_core.projectsmanager.appshandler import AppsHandler
from empower_core.projectsmanager.projectshandler import ProjectsHandler


class ProjectsManager(EService):
    """Projects manager."""

    HANDLERS = [CatalogHandler, AppsHandler, ProjectsHandler,
                AppCallbacksHandler]

    PROJECT_IMPL = Project

    projects = {}

    @property
    def catalog(self):
        """Return workers_package."""

        return walk_module(self.catalog_packages)

    @property
    def catalog_packages(self):
        """Return catalog_packages."""

        return self.params["catalog_packages"]

    @catalog_packages.setter
    def catalog_packages(self, value):
        """Set catalog_packages."""

        self.params["catalog_packages"] = value

    def start(self):
        """Start projects manager."""

        super().start()

        for project in self.PROJECT_IMPL.objects.all():
            self.projects[project.project_id] = project
            self.projects[project.project_id].start_services()

    def create(self, desc, project_id, owner):
        """Create new project."""

        if project_id in self.projects:
            raise ValueError("Project %s already defined" % project_id)

        accounts_manager = srv_or_die("accountsmanager")

        if owner not in accounts_manager.accounts:
            raise KeyError("Username %s not found" % owner)

        project = self.PROJECT_IMPL(project_id=project_id,
                                    desc=desc,
                                    owner=owner)

        project.save()

        self.projects[project_id] = project

        self.projects[project_id].start_services()

        return self.projects[project_id]

    def update(self, project_id, desc):
        """Update project."""

        if project_id not in self.projects:
            raise KeyError("Project %s not found" % project_id)

        project = self.projects[project_id]

        try:
            project.desc = desc
            project.save()
        finally:
            project.refresh_from_db()

        return self.projects[project_id]

    def remove_all(self):
        """Remove all projects."""

        for project_id in list(self.projects):
            self.remove(project_id)

    def remove(self, project_id):
        """Remove project."""

        # Check if project exists
        if project_id not in self.projects:
            raise KeyError("Project %s not registered" % project_id)

        # Fetch project
        project = self.projects[project_id]

        # Stop running services
        self.projects[project_id].stop_services()

        # Delete project from datase and manager
        project.delete()
        del self.projects[project_id]


def launch(context, service_id, catalog_packages=""):
    """ Initialize the module. """

    return ProjectsManager(context=context, service_id=service_id,
                           catalog_packages=catalog_packages)
