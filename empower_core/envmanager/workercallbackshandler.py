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

"""Exposes a RESTful interface ."""

import uuid

import empower_core.apimanager.apimanager as apimanager


# pylint: disable=W0223
class WorkerCallbacksHandler(apimanager.APIHandler):
    """Workers handler."""

    URLS = [r"/api/v1/workers/([a-zA-Z0-9-]*)/callbacks/?",
            r"/api/v1/workers/([a-zA-Z0-9-]*)/callbacks/([a-z]*)/?"]

    @apimanager.validate(min_args=1, max_args=2)
    def get(self, worker_id, callback=None):
        """List the callbacks.

        Args:

            [0]: the worker id (mandatory)
            [1]: the callback (optional)

        Example URLs:

            GET /api/v1/workers/0f91e8ad-1c2a-4b06-97f9-e34097c4c1d0/callbacks
            {
                default: {
                    type: "url",
                    name: "default",
                    callback: "http://www.domain.io/resource"
                }
            }

            GET /api/v1/workers/0f91e8ad-1c2a-4b06-97f9-e34097c4c1d0/
                callbacks/default

            {
                type: "url",
                name: "default",
                callback: "http://www.domain.io/resource"
            }
        """

        worker_id = uuid.UUID(worker_id)
        service = self.service.env.services[worker_id]

        return service.callbacks[callback] if callback else service.callbacks

    @apimanager.validate(returncode=201, min_args=1, max_args=1)
    def post(self, *args, **kwargs):
        """Add a callback.

        Args:

            [0]: the worker id (mandatory)

        Request:

            version: protocol version (1.0)
            name: the name of the callback (mandatory)
            callback: the callback URL (mandatory)

        Example URLs:

            POST /api/v1/workers
            {
                "version": "1.0",
                "name": "default",
                "callback_type": "rest"
                "callback": "http://www.domain.io/resource"
            }
        """

        service_id = uuid.UUID(args[0])
        service = self.service.env.services[service_id]
        service.add_callback(name=kwargs['name'],
                             callback_type=kwargs['callback_type'],
                             callback=kwargs['callback'])

        self.set_header("Location", "/api/v1/workers/%s/callback/%s" %
                        (service.service_id, kwargs['name']))

    @apimanager.validate(returncode=204, min_args=2, max_args=2)
    def delete(self, worker_id, callback):
        """Delete a callback.

        Args:

            [0]: the worker id (mandatory)
            [1]: the callback (mandatory)

        Example URLs:

            DELETE /api/v1/workers/08e14f40-6ebf-47a0-8baa-11d7f44cc228/default
        """

        worker_id = uuid.UUID(worker_id)
        service = self.service.env.services[worker_id]
        service.rem_callback(callback)
