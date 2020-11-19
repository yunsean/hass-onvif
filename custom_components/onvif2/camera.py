"""
Support for ONVIF Cameras with FFmpeg as decoder.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.onvif/
"""
import asyncio
import logging
import os
import sys
import functools as ft
import voluptuous as vol
import onvif013
from onvif013 import exceptions
import pkg_resources

from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    ATTR_ENTITY_ID)
from homeassistant.components.camera import Camera, PLATFORM_SCHEMA, DOMAIN
from homeassistant.components.ffmpeg import (
    DATA_FFMPEG, CONF_EXTRA_ARGUMENTS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_stream)
from homeassistant.helpers.service import extract_entity_ids

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'ONVIF Camera'
DEFAULT_PORT = 5000
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = '888888'
DEFAULT_ARGUMENTS = '-q:v 2'
DEFAULT_PROFILE = 0

CONF_PROFILE = "profile"
CONF_PREVIEW_URL = "preview_url"
CONF_TTS_SENSOR = "tts_sensor"

ATTR_PAN = "pan"
ATTR_TILT = "tilt"
ATTR_ZOOM = "zoom"

DIR_UP = "UP"
DIR_DOWN = "DOWN"
DIR_LEFT = "LEFT"
DIR_RIGHT = "RIGHT"
ZOOM_OUT = "ZOOM_OUT"
ZOOM_IN = "ZOOM_IN"

SERVICE_PTZ = "onvif_ptz"

ONVIF_DATA = "onvif013"
ENTITIES = "entities"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_PREVIEW_URL): cv.string,
    vol.Optional(CONF_TTS_SENSOR): cv.string,
    vol.Optional(CONF_EXTRA_ARGUMENTS, default=DEFAULT_ARGUMENTS): cv.string,
    vol.Optional(CONF_PROFILE, default=DEFAULT_PROFILE):
        vol.All(vol.Coerce(int), vol.Range(min=0)),
})

SERVICE_PTZ_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids,
    ATTR_PAN: vol.In([DIR_LEFT, DIR_RIGHT]),
    ATTR_TILT: vol.In([DIR_UP, DIR_DOWN]),
    ATTR_ZOOM: vol.In([ZOOM_OUT, ZOOM_IN])
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a ONVIF camera."""
    def handle_ptz(service):
        """Handle PTZ service call."""
        pan = service.data.get(ATTR_PAN, None)
        tilt = service.data.get(ATTR_TILT, None)
        zoom = service.data.get(ATTR_ZOOM, None)
        all_cameras = hass.data[ONVIF_DATA][ENTITIES]
        entity_ids = extract_entity_ids(hass, service)
        target_cameras = []
        if not entity_ids:
            target_cameras = all_cameras
        else:
            target_cameras = [camera for camera in all_cameras
                              if camera.entity_id in entity_ids]
        for camera in target_cameras:
            camera.perform_ptz(pan, tilt, zoom)

    hass.services.async_register(DOMAIN, SERVICE_PTZ, handle_ptz,
                                 schema=SERVICE_PTZ_SCHEMA)
    async_add_entities([ONVIFHassCamera(hass, config)])


class ONVIFHassCamera(Camera):
    """An implementation of an ONVIF camera."""

    def __init__(self, hass, config):
        """Initialize a ONVIF camera."""
        super().__init__()
        self._hass = hass
        self._username = config.get(CONF_USERNAME)
        self._password = config.get(CONF_PASSWORD)
        self._preview = config.get(CONF_PREVIEW_URL)
        self._tts = config.get(CONF_TTS_SENSOR)
        self._host = config.get(CONF_HOST)
        self._port = config.get(CONF_PORT)
        self._name = config.get(CONF_NAME)
        self._ffmpeg_arguments = config.get(CONF_EXTRA_ARGUMENTS)
        self._profile_index = config.get(CONF_PROFILE)
        self._input = None
        self._image = None
        self._media_service = None    
        self._ptz_service = None
        self._obtain_input_doing = False
        # _LOGGER.error(os.path.dirname(onvif013.__file__))
        # _LOGGER.error("onvif-py3=" + str(pkg_resources.get_distribution("onvif013-py3").version))
        # _LOGGER.error("suds-py3=" + str(pkg_resources.get_distribution("suds-py3").version))
        # _LOGGER.error("suds-passworddigest-homeassistant=" + str(pkg_resources.get_distribution("suds-passworddigest-homeassistant").version))
        try:
            self._media_service = onvif013.ONVIFService('http://{}:{}/onvif/device_service'.format(self._host, self._port), self._username, self._password, '{}/wsdl/media.wsdl'.format(os.path.dirname(onvif013.__file__)))
        except exceptions.ONVIFError as e:
            _LOGGER.error(e)
            self._media_service = None    

        try:
            self._ptz_service = onvif013.ONVIFService('http://{}:{}/onvif/device_service'.format(self._host, self._port), self._username, self._password, '{}/wsdl/ptz.wsdl'.format(os.path.dirname(onvif013.__file__)))
        except exceptions.ONVIFError as e:
            _LOGGER.error(e)
            self._ptz_service = None

    def obtain_input_uri(self):
        """Set the input uri for the camera."""
        if not self._media_service:
            try:
                self._media_service = onvif013.ONVIFService('http://{}:{}/onvif/device_service'.format(self._host, self._port), self._username, self._password, '{}/wsdl/media.wsdl'.format(os.path.dirname(onvif013.__file__)))
            except exceptions.ONVIFError as e:
                _LOGGER.error(e)
                self._media_service = None  
        if not self._media_service:
            return None
        if self._obtain_input_doing:
            return None
        self._obtain_input_doing = True
        try:
            profiles = self._media_service.GetProfiles()
            if self._profile_index >= len(profiles):
                _LOGGER.warning("ONVIF Camera '%s' doesn't provide profile %d. Using the last profile.", self._name, self._profile_index)
                self._profile_index = -1
            req = self._media_service.create_type('GetStreamUri')
            req.ProfileToken = profiles[self._profile_index]._token
            uri_no_auth = self._media_service.GetStreamUri(req).Uri
            uri_for_log = uri_no_auth.replace('rtsp://', 'rtsp://<user>:<password>@', 1)
            self._input = uri_no_auth.replace('rtsp://', 'rtsp://{}:{}@'.format(self._username, self._password), 1)
            _LOGGER.error("ONVIF Camera Using the following URL for %s: %s", self._name, uri_for_log)
            # we won't need the media service anymore
            self._media_service = None
        except exceptions.ONVIFError as err:
            _LOGGER.error("Couldn't setup camera '%s'. Error: %s", self._name, err)
        self._obtain_input_doing = False
        return None

    def perform_ptz(self, pan, tilt, zoom):
        """Perform a PTZ action on the camera."""
        from onvif013 import exceptions
        if not self._ptz_service:                
            try:
                self._ptz_service = onvif013.ONVIFService('http://{}:{}/onvif/device_service'.format(self._host, self._port), self._username, self._password, '{}/wsdl/ptz.wsdl'.format(os.path.dirname(onvif013.__file__)))
            except:
                self._ptz_service = None
        if self._ptz_service:
            pan_val = 1 if pan == DIR_RIGHT else -1 if pan == DIR_LEFT else 0
            tilt_val = 1 if tilt == DIR_UP else -1 if tilt == DIR_DOWN else 0
            zoom_val = 1 if zoom == ZOOM_IN else -1 if zoom == ZOOM_OUT else 0
            try:
                if pan_val != 0 or tilt_val != 0 or zoom_val != 0:  
                    req = {"Velocity": {"PanTilt": {"_x": pan_val, "_y": tilt_val}, "Zoom": {"_x": zoom_val}}}
                    self._ptz_service.ContinuousMove(req)
                else:
                    req = {"PanTilt": "true", "Zoom": "true"}
                    self._ptz_service.Stop(req)
            except exceptions.ONVIFError as err:
                if "Bad Request" in err.reason:
                    self._ptz_service = None
                    _LOGGER.debug("Camera '%s' doesn't support PTZ.", self._name)
        else:
            _LOGGER.debug("Camera '%s' doesn't support PTZ.", self._name)

    async def async_added_to_hass(self):
        """Handle entity addition to hass."""
        if ONVIF_DATA not in self.hass.data:
            self.hass.data[ONVIF_DATA] = {}
            self.hass.data[ONVIF_DATA][ENTITIES] = []
        self.hass.data[ONVIF_DATA][ENTITIES].append(self)        

    async def async_camera_image(self):
        _LOGGER.error("capture_image")
        from haffmpeg.tools import ImageFrame, IMAGE_JPEG
        if not self._input:
            await self._hass.async_add_executor_job(self.obtain_input_uri)
            if not self._input:
                return None
        ffmpeg = ImageFrame(self.hass.data[DATA_FFMPEG].binary, loop=self.hass.loop)
        self._image = await ffmpeg.get_image(self._input, output_format=IMAGE_JPEG, extra_cmd=self._ffmpeg_arguments)
        return self._image

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        from haffmpeg.camera import CameraMjpeg
        _LOGGER.debug("Handling mjpeg stream from camera '%s'", self._name)
        ffmpeg_manager = self.hass.data[DATA_FFMPEG]
        stream = CameraMjpeg(ffmpeg_manager.binary, loop=self.hass.loop)
        await stream.open_camera(self._input, extra_cmd=self._ffmpeg_arguments)
        try:
            stream_reader = await stream.get_reader()
            return await async_aiohttp_proxy_stream(self.hass, request, stream_reader, ffmpeg_manager.ffmpeg_stream_content_type,)
        finally:
            await stream.close()

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name        

    @property
    async def preview_url(self):
        if self._preview != None and self._preview != "":
            return self._preview
        if not self._input:
            await self._hass.async_add_executor_job(self.obtain_input_uri)
        return self._input
        
    @property
    def tts_sensor(self):
        if self._tts != None and self._tts != "":
            return self._tts
        return None        
