import re


FIRST_LETTERS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
FIRST_LETTER_CHOICES = tuple((letter, letter) for letter in FIRST_LETTERS)

# A letter selected in the interface also includes its accented variants.
# For example, filtering on E keeps Emma as well as Élodie.
FIRST_LETTER_EQUIVALENTS = {
    "A": "AÀÁÂÃÄÅÆ",
    "C": "CÇ",
    "E": "EÈÉÊË",
    "I": "IÌÍÎÏ",
    "N": "NÑ",
    "O": "OÒÓÔÕÖØŒ",
    "U": "UÙÚÛÜ",
    "Y": "YÝŸ",
}


def build_first_letter_regex(first_letters):
    characters = "".join(
        FIRST_LETTER_EQUIVALENTS.get(letter, letter)
        for letter in first_letters
    )
    return rf"^[{re.escape(characters)}]"
