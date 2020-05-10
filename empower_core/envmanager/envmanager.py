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

import empower.workers

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

    def start(self):
        """Start configuration manager."""

        super().start()

        if not self.ENV_IMPL.objects.all().count():
            self.ENV_IMPL(project_id=uuid.uuid4()).save()

        self.env = self.ENV_IMPL.objects.first()
        self.env.start_services()

    @property
    def catalog(self):
        """Return available workers."""

        return walk_module(empower.workers)


def launch(context, service_id):
    """ Initialize the module. """

    return EnvManager(context=context, service_id=service_id)
