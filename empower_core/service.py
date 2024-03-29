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

"""Service."""

import uuid
import logging
import types

from urllib.parse import urlparse

import requests
import tornado.ioloop

from empower_core.imsi import IMSI
from empower_core.plmnid import PLMNID
from empower_core.etheraddress import EtherAddress
from empower_core.ssid import SSID
from empower_core.serialize import serializable_dict
from empower_core.serialize import serialize

CALLBACK_NATIVE = "native"
CALLBACK_REST = "rest"

CALLBACK_TYPES = [CALLBACK_NATIVE, CALLBACK_REST]


@serializable_dict
class EService:
    """Base service class."""

    HANDLERS = []

    def __init__(self, context, service_id, **kwargs):

        # Declaration
        self._service_id = None

        # Pointer to an Env or a Project object (can be None)
        self.context = context

        # Set the service id
        self.service_id = service_id

        # If every is not specified then disable periodic loop
        if 'every' not in kwargs:
            kwargs['every'] = -1

        # Service's callbacks
        self.callbacks = dict()

        # Set logger
        self.log = logging.getLogger(self.name)

        # Worker process, set only if every > 0
        self.worker = None

        # Persistent dict
        self.configuration = {}

        # Service parameters
        self.params = {}

        # Set service parameters
        for param in kwargs:
            setattr(self, param, kwargs[param])

    def validate_param(self, param, value):
        """Validate the parameter using the manifest."""

        if param not in self.manifest['params']:
            raise ValueError("Invalid paramer: %s" % param)

        manifest = self.manifest['params'][param]
        static = manifest.get('static', False)

        if param in self.params and static:
            raise ValueError("Parameter cannot be modified: %s" % param)

        if not value and not manifest['mandatory']:
            return manifest['default']

        if not value and manifest['mandatory']:
            raise ValueError("Parameter %s cannot be null" % param)

        param_type = manifest['type']

        cast_dict = {
            "str": str,
            "int": int,
            "IMSI": IMSI,
            "PLMNID": PLMNID,
            "SSID": SSID,
            "EtherAdress": EtherAddress
        }

        # try to cast value to specified type
        if isinstance(param_type, str):

            if param_type not in cast_dict:
                raise ValueError("Invalid value for '%s' expected '%s'" %
                                 (param, param_type))

            param_type_class = cast_dict[param_type]
            return param_type_class(value)

        # check if in the list
        if isinstance(param_type, list):

            if value in param_type:
                return value

            raise ValueError("Invalid value for '%s' valid '%s' got '%s'" %
                             (param, ','.join(str(x) for x in param_type),
                              value))

        # value is invalid
        raise ValueError("Invalid value for '%s': %s" % (param, value))

    def save_service_state(self):
        """Save service state."""

        if not self.context:
            return

        self.context.save_service_state(self.service_id)

    def register_service(self, name, **kwargs):
        """Register a service.

        If a service with the same name and parameters is already running, then
        that service instance will be returned. Otherwise a new service will be
        spawned."""

        if not self.context:
            return None

        return self.context.register_service(name, params=kwargs)

    def unregister_service(self, service_id):
        """Unregister a service."""

        if not self.context:
            return None

        return self.context.unregister_service(service_id)

    def handle_callbacks(self, params=None, name="default"):
        """Invoke registered callbacks."""

        if name not in self.callbacks:
            return

        callback_type = self.callbacks[name]['callback_type']
        argument = params if params else self
        callback = self.callbacks[name]['callback']

        self.log.info("Handling callback %s (%s)", name, callback_type)

        try:

            # if type is native just invoke it with the specified params
            if self.callbacks[name]['callback_type'] == CALLBACK_NATIVE:
                callback(argument)
                return

            # if type is REST make a post with the serialized params
            if self.callbacks[name]['callback_type'] == CALLBACK_REST:
                response = requests.post(url=callback,
                                         json=serialize(argument))
                self.log.info("POST %s - %u", callback, response.status_code)

        except Exception as ex:
            self.log.exception(ex)

    def add_callback(self, callback, name="default",
                     callback_type=CALLBACK_NATIVE):
        """Add a new callback."""

        if 'callbacks' not in self.manifest:
            raise KeyError("Callback %s not defined" % name)

        if name not in self.manifest['callbacks']:
            raise KeyError("Callback %s not defined" % name)

        if callback_type not in CALLBACK_TYPES:
            raise ValueError("Invalid callback type: %s" % callback_type)

        # native callbacks are not save to the service state
        if callback_type == CALLBACK_NATIVE:

            if not isinstance(callback,
                              (types.FunctionType, types.MethodType)):

                raise ValueError("Callback not callable")

            self.callbacks[name] = {
                "name": name,
                "callback": callback,
                "callback_type": CALLBACK_NATIVE
            }

            return

        # rest callbacks can be saved to service state
        if callback_type == CALLBACK_REST:

            self.callbacks[name] = {
                "name": name,
                "callback": urlparse(callback).geturl(),
                "callback_type": CALLBACK_REST
            }

            self.save_service_state()

            return

        raise ValueError("Invalid input to add callback")

    def rem_callback(self, name="default"):
        """Remove a callback."""

        del self.callbacks[name]
        self.save_service_state()

    def to_dict(self):
        """Return JSON-serializable representation of the object."""

        output = {}

        output['service_id'] = self.service_id

        output['name'] = self.name
        output['callbacks'] = self.callbacks
        output['params'] = self.params

        if self.context:
            output['project_id'] = self.context.project_id
            output['manifest'] = self.manifest

        return output

    @property
    def name(self):
        """Get name."""

        return "%s" % self.__class__.__module__

    @property
    def manifest(self):
        """Get manifest."""

        return self.context.manager.catalog[self.name]

    @property
    def service_id(self):
        """Get service_id."""

        return self._service_id

    @service_id.setter
    def service_id(self, value):
        """Set service_id."""

        if isinstance(value, uuid.UUID):
            self._service_id = value
        else:
            self._service_id = uuid.UUID(value)

    @property
    def every(self):
        """Return loop period."""

        return self.params["every"]

    @every.setter
    def every(self, value):
        """Set loop period."""

        self.params["every"] = int(value)

        if self.worker:
            self.stop()
            self.start()

    def write_points(self, points):
        """Write points to context."""

        self.context.write_points(points)

    def start(self):
        """Start control loop."""

        # Not supposed to run a loop
        if self.every == -1:
            return

        # Start the control loop
        self.worker = \
            tornado.ioloop.PeriodicCallback(self.loop, self.every)

        self.worker.start()

    def stop(self):
        """Stop control loop."""

        # save state
        self.save_service_state()

        # Not supposed to run a loop
        if self.every == -1:
            return

        # stop the control loop
        self.worker.stop()
        self.worker = None

    def loop(self):
        """Control loop."""

        self.log.info("Empty loop")

    def to_str(self):
        """Return an ASCII representation of the object."""

        return "%s" % self.name

    def __str__(self):
        return self.to_str()

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, EService):
            return self.name == other.name and self.every == other.every
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.__class__.__name__ + "('" + self.to_str() + "')"
