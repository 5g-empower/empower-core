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

"""Conf manager."""

import uuid

from empower_core.walkmodule import walk_module
from empower_core.service import EService
from empower_core.envmanager.env import Env
from empower_core.envmanager.workercallbackshandler import \
    WorkerCallbacksHandler
from empower_core.envmanager.workershandler import WorkersHandler
from empower_core.envmanager.cataloghandler import CatalogHandler
from empower_core.envmanager.envhandler import EnvHandler


class EnvManager(EService):
    """Environment manager."""

    HANDLERS = [WorkersHandler, WorkerCallbacksHandler, CatalogHandler,
                EnvHandler]

    ENV_IMPL = Env

    env = None

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
        """Start configuration manager."""

        super().start()

        if not self.ENV_IMPL.objects.all().count():
            self.ENV_IMPL(project_id=uuid.uuid4()).save()

        self.env = self.ENV_IMPL.objects.first()
        self.env.start_services()


def launch(context, service_id, catalog_packages=""):
    """ Initialize the module. """

    return EnvManager(context=context, service_id=service_id,
                      catalog_packages=catalog_packages)
