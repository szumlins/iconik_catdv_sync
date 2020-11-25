import json
import logging
import logging.handlers
import multiprocessing
import os
import signal
import re
from pymediainfo import MediaInfo
from pymediainfo import Track

#set up our log
logger = logging.getLogger("iconik-proxy")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.handlers.RotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + "/logs/proxy.log", maxBytes=104857600,backupCount=5)
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def get_start_time_code(media_info):
    tc_track = None
    video_track = None
    tc = None

    for track in media_info.tracks:
        if track.track_type == "Other" and track.type == "Time code":
            tc_track = track
        if track.track_type == "Video":
            video_track = track

    if tc_track and tc_track.time_code_of_first_frame:
        tc = tc_track.time_code_of_first_frame

    if not tc and video_track and video_track.time_code_of_first_frame:
        tc = video_track.time_code_of_first_frame

    if tc:
        match = re.search('(\d\d)([:;,\.])(\d\d)([:;,\.])(\d\d)([:;,\.])(\d\d)', tc)
        if match:
            logger.debug("Matched timecode: %s" % str(match))
            if match.group(6) in [";", ","]:
                return "{}:{}:{};{}".format(
                    match.group(1),
                    match.group(3),
                    match.group(5),
                    match.group(7)
                )
            else:
                return "{}:{}:{}:{}".format(
                    match.group(1),
                    match.group(3),
                    match.group(5),
                    match.group(7)
                )

    return None

def get_track(media_info, track_type):
    """
    Returns a track object for a requested track type
    """
    for track in media_info.tracks:
        if track.track_type == track_type:
            return track


def get_duration(media_info):
    """

    Returns the duration in milliseconds or None if the item doesn't
    have a duration

    """

    if get_track(media_info, 'Video'):
        return get_track(media_info, 'Video').duration
    elif get_track(media_info, 'Audio'):
        return get_track(media_info, 'Audio').duration
    else:
        return None


def get_image_resolution(media_info):
    """

    Returns Image resolution, or None if no image

    """

    if not get_track(media_info, 'Image'):
        return None

    return [
        get_track(media_info, 'Image').width,
        get_track(media_info, 'Image').height
    ]


def get_mediainfo(url):
    """

    Returns a MediaInfo object for a URL to be used
    in other calls in this package

    """

    media_info = MediaInfo.parse(url) #, mediainfo_options={"File_TestContinuousFileNames": "0"})
    return media_info

def get_lowres_video_info(full_path, start_time_code=None, is_drop_frame_value=None):
    try:
        file_size = os.path.getsize(full_path)
    except FileNotFoundError:
        raise MediaInfoException('Lowres file not found')

    if file_size == 0:
        raise MediaInfoException('Lowres file is empty')

    try:
        media_info = get_mediainfo(full_path)
    except FileNotFoundError:
        raise MediaInfoException('Lowres file not found/empty')
    try:
        general_track = next(track for track in media_info.tracks if track.track_type == 'General')
        video_track = next(track for track in media_info.tracks if track.track_type == 'Video')
    except StopIteration:
        raise MediaInfoException('Lowres does not have the correct media tracks')

    result = {
        'format': general_track.format,
        'codec': video_track.format,
        'bit_rate': video_track.bit_rate,
        'resolution': {
            'width': video_track.width,
            'height': video_track.height,
        },
        'frame_rate': video_track.frame_rate or FALLBACK_VIDEO_FRAME_RATE,
    }

    if start_time_code:
        logger.debug("Using TimeCode from source media")
        result['start_time_code'] = start_time_code
    else:
        result['start_time_code'] = get_start_time_code(media_info)

    if is_drop_frame_value is None:
        result['is_drop_frame'] = is_drop_frame(video_track)
    else:
        logger.debug("Using is_drop_frame value from source media")
        result['is_drop_frame'] = is_drop_frame_value

    logger.debug("Lowres media info: ")

    return result

def is_drop_frame(mediainfo_video_track):
    delay_drop_frame = mediainfo_video_track.delay_dropframe
    if delay_drop_frame is not None:
        return delay_drop_frame == 'Yes'

    if mediainfo_video_track.delay_settings:
        if mediainfo_video_track.delay_settings.find("DropFrame=Yes") >= 0:
            return True

def get_proxy_metadata(full_path, start_time_code=None, is_drop_frame=None):

    media_info = get_mediainfo(full_path)
    video = get_track(media_info, 'Video')
    image = get_track(media_info, 'Image')
    audio = get_track(media_info, 'Audio')
    general = get_track(media_info, 'General')

    if video:
        logger.debug("Getting lowres mediainfo")
        metadata = get_lowres_video_info(full_path, start_time_code, is_drop_frame)
    elif audio:
        metadata = {
            'codec': audio.format or audio.codec_family or general.format or "",
            'bit_rate': audio.sampling_rate or 0,
            'format': general.format or audio.format or "",
            'frame_rate': '1000',
            'is_drop_frame': False
        }
    elif image:
        metadata = {
            'codec': image.format or image.codec_family or general.format or "",
            'bit_rate': image.bit_depth or 0,
            'format': general.format or image.format or "",
            'resolution': {
                'width': image.width,
                'height': image.height,
            },
            'frame_rate': '0',
            'is_drop_frame': False,
            'start_time_code': None,
        }
    else:
        metadata = {
            'codec': general.format or "",
            'bit_rate': general.bit_rate or 0,
            'format': general.format or "",
            'frame_rate': '0',
            'is_drop_frame': False
        }

    return metadata


def is_pdf_format(media_info):
    if not media_info:
        return False

    general = get_track(media_info, "General")
    text = get_track(media_info, "Text")

    return general and text and general.format == "PDF" and text.format == "PDF"


def run_media_info(f, q, t):
    try:
        q.put(get_mediainfo(f), timeout=t)
    except FileNotFoundError:
        q.put(None)


class MediaInfoTrack(Track):
    def __init__(self, values):
        self.__dict__.update(values)


class MediaInfoCustom(MediaInfo):
    def __init__(self):
        self.xml_dom = None
        self._tracks = []

    def from_json(self, data):
        self._tracks = []
        for track in data.get('tracks', []):
            self._tracks.append(MediaInfoTrack(track))

def media_info_from_json(media_info_json):
    media_info = MediaInfoCustom()
    if media_info_json:
        try:
            media_info.from_json(json.loads(media_info_json))
        except json.JSONDecodeError:
            pass
    return media_info
