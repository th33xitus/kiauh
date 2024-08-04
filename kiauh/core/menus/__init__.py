# ======================================================================= #
#  Copyright (C) 2020 - 2024 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


@dataclass
class Option:
    """
    Represents a menu option.
    :param method: Method that will be used to call the menu option
    :param menu: Flag for singaling that another menu will be opened
    :param opt_index: Can be used to pass the user input to the menu option
    :param opt_data: Can be used to pass any additional data to the menu option
    """

    method: Callable | None = None
    menu: bool = False
    opt_index: str = ""
    opt_data: Any = None


class FooterType(Enum):
    QUIT = "QUIT"
    BACK = "BACK"
    BACK_HELP = "BACK_HELP"
    BLANK = "BLANK"
