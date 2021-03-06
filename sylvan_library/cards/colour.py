colour_name_to_flag = {
    'white': 1,
    'blue': 2,
    'black': 4,
    'red': 8,
    'green': 16,
}

colour_code_to_flag = {
    'w': 1,
    'u': 2,
    'b': 4,
    'r': 8,
    'g': 16,
}


class Colour:
    white = 1
    blue = 2
    black = 4
    red = 8
    green = 16

    all = white | blue | black | red | green
    none = 0


def colour_names_to_flags(colour_names):
    flags = 0
    for colour in colour_names:
        flags |= colour_name_to_flag[colour.lower()]

    return flags


def colour_codes_to_flags(colour_codes):
    flags = 0
    for colour in colour_codes:
        flags |= colour_code_to_flag[colour.lower()]

    return flags
