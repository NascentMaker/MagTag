# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time

import adafruit_requests
import alarm
import board
import rtc
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
from adafruit_oauth2 import OAuth2

from constants import (
    MAX_BACKOFF_COUNT,
    MAXIMUM_BACKOFF,
    REFRESH_TIME,
    MAX_EVENTS,
    MINIMUM_BACKOFF,
    MONTHS,
    SLEEP_MEMORY_SLOT_BACKOFF_TIMES,
    SLEEP_MEMORY_SLOT_BACKOFF,
    WEEKDAYS,
    WEATHER_ICONS,
)


def deep_sleep(backoff: bool = False) -> None:
    magtag.peripherals.neopixel_disable = True
    magtag.peripherals.speaker_disable = True
    if backoff:
        sleep_length = alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF]
        print(f'ERROR, EXPONENTIAL BACKOFF: Sleeping for {sleep_length} seconds.')
        backoff_alarm = alarm.time.TimeAlarm(monotonic_time=int(time.monotonic()) + sleep_length)
        alarm.exit_and_deep_sleep_until_alarms(backoff_alarm)
    print(f'Sleeping for {REFRESH_TIME:d} minutes')
    alarm.exit_and_deep_sleep_until_alarms(pin_alarm, time_alarm)


def deep_sleep_exponential_backoff() -> None:
    sleep_time = alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF]
    backoff_count = alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF_TIMES]
    if not sleep_time:
        sleep_time = MINIMUM_BACKOFF
        backoff_count = 0
    if MINIMUM_BACKOFF < sleep_time < MAXIMUM_BACKOFF:
        sleep_time *= 2
    backoff_count += 1
    alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF] = sleep_time
    alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF_TIMES] = backoff_count
    if backoff_count >= MAX_BACKOFF_COUNT:
        raise ConnectionError('Unable to connect after backoff expired')
    deep_sleep(backoff=True)


def clear_backoff() -> None:
    alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF] = 0
    alarm.sleep_memory[SLEEP_MEMORY_SLOT_BACKOFF_TIMES] = 0


# Set up alarms for the different buttons and timer
pin_alarm = alarm.pin.PinAlarm(board.D14, value=False)
time_alarm = alarm.time.TimeAlarm(monotonic_time=int(time.monotonic()) + (REFRESH_TIME * 60))

# Create a new MagTag object
magtag = MagTag(debug=True)
r = rtc.RTC()

# Handle pin alarm
if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
    print(f'Light level: {magtag.peripherals.light}')
    # Check what the light level is before we blind someone
    NEOPIXEL_BRIGHTNESS = 0.25
    if magtag.peripherals.light < 700:
        NEOPIXEL_BRIGHTNESS = 0.5
    if magtag.peripherals.light < 1500:
        NEOPIXEL_BRIGHTNESS = 0.75
    if magtag.peripherals.light < 2000:
        NEOPIXEL_BRIGHTNESS = 1
    magtag.peripherals.neopixel_disable = False
    magtag.peripherals.neopixels.brightness = NEOPIXEL_BRIGHTNESS
    magtag.peripherals.neopixels.fill(0xFFDD77)
    magtag.peripherals.neopixels.show()
    time.sleep(3)
    deep_sleep()
elif isinstance(alarm.wake_alarm, alarm.time.TimeAlarm):
    for i in range(4):
        time.sleep(0.5)
        magtag.peripherals.neopixels[0] = (255, 255, 0)
        time.sleep(0.25)
        magtag.peripherals.neopixels[0] = (0, 0, 0)

magtag.peripherals.neopixels[0] = (0, 15, 0)

# DisplayIO Setup
magtag.set_background(0xFFFFFF)

# Add the header
line_header = Line(7, 30, 220, 30, color=0x666666)

# Set up calendar event fonts
font_event = bitmap_font.load_font("fonts/NotoSans-Regular-12.pcf")
font_h1 = bitmap_font.load_font("fonts/Spartan-Black-13.pcf")
font_weather = bitmap_font.load_font("fonts/WeatherIcons-Regular-48.pcf")

label_header = label.Label(font_h1, x=7, y=16, color=0x000000)
forecast_icon = label.Label(font_weather, color=0x666666, anchor_point=(0.5, 0.5), anchored_position=(255, 35))
forecast_temp = label.Label(font_h1, color=0x666666, anchor_point=(0.5, 0.5), anchored_position=(255, 70))

magtag.splash.append(forecast_icon)
magtag.splash.append(forecast_temp)
magtag.splash.append(line_header)
magtag.splash.append(label_header)

# noinspection PyProtectedMember
secrets = magtag.network._secrets

if magtag.peripherals.battery < 3.5:
    print("I need to be charged")
    for i in range(3):
        magtag.peripherals.play_tone(2600, 0.1)
        time.sleep(0.2)

# Connect to the network
print("Connecting to network and fetching weather...")
forecast = magtag.network._get_io_client().receive_weather(secrets["weather_location_id"])
print("Connected.")

forecast_icon.text = chr(WEATHER_ICONS[f'{forecast["forecast_hours_2"]["icon"]}'])
forecast_temp.text = f'{forecast["forecast_hours_2"]["temperature"]:.1f}°F'

# Initialize an OAuth2 object with GCal API scope
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
google_auth = OAuth2(
    magtag.network.requests,
    secrets["google_client_id"],
    secrets["google_client_secret"],
    scopes,
    secrets["google_access_token"],
    secrets["google_refresh_token"],
)


def get_current_time(max_time=False, cur_time=None):
    """
    Gets local time from Adafruit IO and converts to RFC3339 timestamp.
    """

    if not max_time and not cur_time:
        # Get local time from Adafruit IO
        try:
            magtag.get_local_time(location=secrets["timezone"])
        except RuntimeError:
            deep_sleep_exponential_backoff()

    # Format as RFC339 timestamp
    cur_time = r.datetime

    if max_time:  # maximum time to fetch events is midnight (4:59:59UTC)
        cur_time_max = time.struct_time((
            cur_time[0],
            cur_time[1],
            cur_time[2] + 1,
            4,
            59,
            59,
            cur_time[6],
            cur_time[7],
            cur_time[8],
        ))
        cur_time = cur_time_max
    cur_time = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}{:s}".format(
        cur_time[0],
        cur_time[1],
        cur_time[2],
        cur_time[3],
        cur_time[4],
        cur_time[5],
        "Z",
    )
    return cur_time


def get_calendar_events(calendar_id: str, max_events: int, time_min: int) -> [object]:
    """
    Returns events on a specified calendar.
    Response is a list of events ordered by their start date/time in ascending order.
    :param calendar_id: ID of calendar, can sometimes be your email address
    :param max_events: Number of events to fetch
    :param time_min: Earliest time to fetch events from
    """

    # parse the 'items' array, so we can iterate over it easier
    items = []

    headers = {
        "Authorization": "Bearer " + google_auth.access_token,
        "Accept": "application/json",
        "Content-Length": "0",
    }
    url = (
        "https://www.googleapis.com/calendar/v3/calendars/{0}"
        "/events?maxResults={1}&timeMin={2}&timeMax={3}&orderBy=startTime"
        "&singleEvents=true".format(calendar_id, max_events, time_min, time_max)
    )

    print("Fetching calendar events from {0} to {1}".format(time_min, time_max))

    try:
        resp = magtag.network.fetch(url, headers=headers)
        resp_items = None
        if magtag.network.check_response(resp):
            resp_json = resp.json()
            resp_items = resp_json["items"]
            resp.close()
        if not resp_items:
            print("No events scheduled for today!")
        for event in range(0, len(resp_items)):
            items.append(resp_items[event])
    except (RuntimeError, ConnectionError) as ex:
        print(f'ERROR: Could not fetch events: {ex}')
        deep_sleep_exponential_backoff()
    return items


def format_datetime(datetime, pretty_date=False):
    """
    Formats ISO-formatted datetime returned by Google Calendar API into
    a struct_time.
    :param str datetime: Datetime string returned by Google Calendar API
    :param pretty_date: Should the date be formatted
    :return: struct_time
    """

    times = datetime.split("T")
    the_date = times[0]
    the_time = times[1]
    year, month, mday = [int(x) for x in the_date.split("-")]
    the_time = the_time.split("-")[0]
    if "Z" in the_time:
        the_time = the_time.split("Z")[0]
    hours, minutes, _ = [int(x) for x in the_time.split(":")]
    formatted_time = "{:02d}:{:02d}".format(hours, minutes)
    if pretty_date:  # return a nice date for header label
        formatted_date = "{} {} {:02d}, {:04d} ".format(
            WEEKDAYS[r.datetime[6]], MONTHS[month], mday, year
        )
        return formatted_date
    # Event occurs today, return the time only
    return formatted_time


def display_calendar_events(resp_events):
    # Display all calendar events
    for event_idx in range(len(resp_events)):
        event = resp_events[event_idx]
        # wrap event name around second line if necessary
        event_desc_x_position = 7
        event_desc_length = 40
        if "dateTime" in event["start"]:
            if event_idx < 3:
                event_desc_length = 28
            event_desc_x_position = 52
            event_start = format_datetime(event["start"]["dateTime"])
            # Generate labels holding event info
            label_event_time = label.Label(
                font_event,
                x=7,
                y=46 + (event_idx * 20),
                color=0x000000,
                text=event_start,
            )
            magtag.splash.append(label_event_time)

        event_name = magtag.wrap_nicely(event["summary"], event_desc_length)
        event_name = "\n".join(event_name[0:1])  # only wrap 1 line, truncate the rest...

        label_event_desc = label.Label(
            font_event,
            x=event_desc_x_position,
            y=46 + (event_idx * 20),
            color=0x000000,
            text=event_name,
            line_spacing=0.95,
        )
        magtag.splash.append(label_event_desc)


magtag.peripherals.neopixels[0] = (0, 255, 0)

access_token_obtained = 0
refresh_token_fail_text = 'Unable to refresh access token - has the token been revoked?'
now = 0

try:
    print("fetching local time...")
    now = get_current_time()
    time_max = get_current_time(max_time=True, cur_time=now)

    if not google_auth.refresh_access_token():
        magtag.peripherals.neopixels[0] = (255, 0, 0)
        print(refresh_token_fail_text)
        deep_sleep_exponential_backoff()
    access_token_obtained = int(time.monotonic())
except (RuntimeError, adafruit_requests.OutOfRetries) as ex:
    print(f'ERROR: Could not get refresh token: {ex}')
    deep_sleep_exponential_backoff()

while True:
    # check if we need to refresh token
    if (
            int(time.monotonic()) - access_token_obtained
            >= google_auth.access_token_expiration
    ):
        print("Access token expired, refreshing...")
        try:
            if not google_auth.refresh_access_token():
                magtag.peripherals.neopixels[0] = (255, 0, 0)
                print(refresh_token_fail_text)
                deep_sleep_exponential_backoff()
            access_token_obtained = int(time.monotonic())
        except (RuntimeError, adafruit_requests.OutOfRetries) as ex:
            print(f'ERROR (while True): Could not get refresh token: {ex}')
            deep_sleep_exponential_backoff()

    magtag.peripherals.neopixels[0] = (255, 255, 0)

    # setup header label
    label_header.text = format_datetime(now, pretty_date=True)

    # fetch calendar events!
    print("fetching calendar events...")
    events = get_calendar_events(secrets["calendar_id"], MAX_EVENTS, now)

    print("displaying events")
    display_calendar_events(events)

    magtag.peripherals.neopixels[0] = (0, 255, 0)

    board.DISPLAY.show(magtag.splash)
    board.DISPLAY.refresh()

    clear_backoff()
    deep_sleep()
