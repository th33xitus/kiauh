#!/bin/bash

#=======================================================================#
# Copyright (C) 2020 - 2022 Dominik Willner <th33xitus@gmail.com>       #
#                                                                       #
# This file is part of KIAUH - Klipper Installation And Update Helper   #
# https://github.com/th33xitus/kiauh                                    #
#                                                                       #
# This file may be distributed under the terms of the GNU GPLv3 license #
#=======================================================================#

set -e

function remove_ui(){
  top_border
  echo -e "|     ${red}~~~~~~~~~~~~~~ [ Remove Menu ] ~~~~~~~~~~~~~~${white}     | "
  hr
  echo -e "|  ${yellow}INFO:${white}                                                | "
  echo -e "|  Printer configs or backups always remain untouched!  | "
  hr
  echo -e "|  Firmware:                |  Touchscreen GUI:         | "
  echo -e "|  1) [Klipper]             |  5) [KlipperScreen]       | "
  echo -e "|                           |                           | "
  echo -e "|  Klipper API:             |  Other:                   | "
  echo -e "|  2) [Moonraker]           |  6) [OctoPrint]           | "
  echo -e "|                           |  7) [PrettyGCode]         | "
  echo -e "|  Klipper Webinterface:    |  8) [Telegram Bot]        | "
  echo -e "|  3) [Mainsail]            |  9) [MJPG-Streamer]       | "
  echo -e "|  4) [Fluidd]              | 10) [NGINX]               | "
  back_footer
}

function remove_menu(){
  do_action "" "remove_ui"
  while true; do
    read -p "${cyan}Perform action:${white} " action; echo
    case "${action}" in
      1)
        do_action "remove_klipper" "remove_ui";;
      2)
        do_action "remove_moonraker" "remove_ui";;
      3)
        do_action "remove_mainsail" "remove_ui";;
      4)
        do_action "remove_fluidd" "remove_ui";;
      5)
        do_action "remove_klipperscreen" "remove_ui";;
      6)
        do_action "remove_octoprint" "remove_ui";;
      7)
        do_action "remove_prettygcode" "remove_ui";;
      8)
        do_action "remove_MoonrakerTelegramBot" "remove_ui";;
      9)
        do_action "remove_mjpg-streamer" "remove_ui";;
      10)
        do_action "remove_nginx" "remove_ui";;
      B|b)
        clear; main_menu; break;;
      *)
        deny_action "remove_ui";;
    esac
  done
  remove_menu
}
