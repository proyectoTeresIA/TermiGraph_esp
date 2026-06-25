UNTERM_VALUES = {
    "normAuth": {
        "[deprecated]": "deprecatedTerm",
        "[superseded]": "supersededTerm"
    }
}

NOT_PUBLIC_RECS = ['verification']


FIELD_COUNTER = {
    0: {
        "fieldType": "preferred_term",
        "normAuth": "preferredTerm"
    },
    1: {
        "fieldType": "term_source"
    },
    2:{
        "fieldType": "term_note"
    },
    3: {
        "fieldType": "term_context"
    },
    4: {
        "fieldType": "alternate_term"
    },
    5: {
        "fieldType": "term_source"
    },
    6: {
        "fieldType": "term_note"
    },
    7: {
        "fieldType": "term_context"
    },
    8: {
        "fieldType": "acronym",
        "termType": "shortForm"
    },
    9: {
        "fieldType": "term_source"
    },
    10: {
        "fieldType": "term_note"
    },
    11: {
        "fieldType": "term_context"
    },
    12: {
        "fieldType": "language_validation"
    },
    13: {
        "fieldType": "definition" 
    },
    14: {
        "fieldType": "note"
    }
}

TERM_CLEANER = [
    "<br>", "</span>", "<span[^>]*>"
]