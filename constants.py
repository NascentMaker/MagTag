# Maximum amount of events to display
MAX_EVENTS = 4

# Amount of time to wait between refreshing the calendar, in minutes
REFRESH_TIME = 30

# Shortest time we will wait for backoff
MINIMUM_BACKOFF = 15

# Maximum length of backoff in seconds (5 minutes)
MAXIMUM_BACKOFF = 60*5

MAX_BACKOFF_COUNT = 60/5

# Constants used in sleep_memory to indicate error
SLEEP_MEMORY_SLOT_BACKOFF = 1
SLEEP_MEMORY_SLOT_BACKOFF_TIMES = 2

# Dict. of month names for pretty-printing the header
MONTHS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
# Dict. of day names for pretty-printing the header
WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

# Dict, of weather icon unicode characters
WEATHER_ICONS = {
    'clear-day': 0xf00d,
    'clear-night': 0xf02e,
    'rain': 0xf019,
    'snow': 0xf01b,
    'sleet': 0xf0b5,
    'wind': 0xf050,
    'fog': 0xf014,
    'cloudy': 0xf013,
    'partly-cloudy-day': 0xf002,
    'partly-cloudy-night': 0xf031,
    'hail': 0xf015,
    'thunderstorm': 0xf01e,
    'tornado': 0xf056,
}
