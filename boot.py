# SPDX-FileCopyrightText: 2021 Torgny Bjers, written for THE LULZ
#
# SPDX-License-Identifier: Unlicense

import alarm

if alarm.wake_alarm:
    if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
        alarm.sleep_memory[0] = True
