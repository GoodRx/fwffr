"""
Utilities related to parsing files
"""

from collections import OrderedDict
import sys

PY3 = sys.version_info[0] == 3

__all__ = [
    'FixedLengthError',
    'FixedLengthUnknownRecordTypeError',
    'FixedLengthSeparatorError',
    'FixedLengthJustificationError',
    'FixedLengthFieldParser',
]

if PY3:
    def iteritems(d, **kw):
        return iter(d.items(**kw))
else:
    def iteritems(d, **kw):
        return d.iteritems(**kw)


class FixedLengthError(ValueError):
    """ Base class for parsing errors """


class FixedLengthUnknownRecordTypeError(FixedLengthError):
    """ Unknown record type encountered error

    Arguments:
        record_type (str): The type indicator of the unrecognized record.
    """
    MESSAGE = "Unknown record type %r encountered"

    def __init__(self, record_type):
        self.record_type = record_type
        super(FixedLengthUnknownRecordTypeError, self).__init__(
            self.MESSAGE % (record_type,)
        )

class FixedLengthSeparatorError(FixedLengthError):
    """ Separator not found error

    Arguments:
        field (str):
            The name of the field that has no separator before it.
        pointer (int):
            The zero-indexed offset into the record where the separator was
            expected.
    """
    MESSAGE = "No field separator found before %r at %d"

    def __init__(self, field, pointer):
        self.field = field
        self.pointer = pointer
        super(FixedLengthSeparatorError, self).__init__(
            self.MESSAGE % (field, pointer)
        )


class FixedLengthJustificationError(FixedLengthError):
    """ Justification error

    Arguments:
        field (str):
            The name of the field that was not justified correctly.
        value (str):
            The value of the malformed field.
    """
    MESSAGE = "Field %r value %r is not justified correctly"

    def __init__(self, field, value):
        self.field = field
        self.value = value
        super(FixedLengthJustificationError, self).__init__(
            self.MESSAGE % (field, value)
        )


class FixedLengthFieldParser(object):
    """
    Utility to parse and read from fixed-length field files.

    For these classes, process_fixed_length_record should be passed a sequence
    of (field_name, field_length) tuples.  The record will be parsed, and
    validation will be run to ensure that the file is not malformed.

    file_obj
        The file-like object to parse.
    fields
        Field specification. For files with homogeneous records, this should be
        a list of tuples in the form (field_name, length_of_field), or an
        OrderedDict with items in the same format. For files that combine
        different types of records in the same file, a dictionary can be passed
        whose keys are record type indicators, and whose values are in the
        previously described format for fields. For these files, the
        record_type_func parameter MUST be passed.
    record_type_func
        For files with multiple record types, this must be a function that
        accepts a line from the file and returns a key into the fields dict.
        For simple usage, a simple utility function
        FixedLengthFieldParser.generate_type_from_offset_func is provided,
        which generates a suitable function from a position and offset.
    override_justification_error_func
        Provide a hook to override justification errors for known issues
        Should return None or the corrected value for the field
    field_separator
        A string or None indicating a separator between the fixed-length
        fields.  If provided, the existence of the separator between fields
        will be checked for, and an error will be raised if it is not found.
        Providing a field separator will disable the starting-whitespace check.
    right_justified
        A list of fields that are right-justified instead of left.
    skip_justified
        A list of fields that aren't justfiied.
    encoding
        The base encoding of the file. If set, all values will be decoded.
    skip_unknown_types
        For files with multiple record types, indicate whether an unknown type
        should result in a ValueError or silently pass.
    """

    def __init__(self, file_obj, fields, record_type_func=None,
                 override_justification_error_func=None, field_separator=None,
                 right_justified=(), skip_justified=(), encoding=None,
                 skip_unknown_types=True, strip=True):
        self.file_obj = file_obj
        self.fields = fields
        self.record_type_func = record_type_func
        self.override_justification_error_func = (
            override_justification_error_func or (lambda f, v: None)
        )
        self.field_separator = field_separator
        self.right_justified = right_justified
        self.skip_justified = skip_justified
        self.encoding = encoding
        self.skip_unknown_types = skip_unknown_types
        self.strip = True

    def __iter__(self):
        for line in self.file_obj:
            result = self.process_fixed_length_record(line)
            if result is not None:
                yield result

    def process_fixed_length_record(self, record_line):
        """
        Given the raw fixed-length record line, returns two dictionaries: the
        raw fields, and the processed and converted fields
        """
        record = {}

        pointer = 0
        field_sep = self.field_separator or ''
        field_sep_len = len(field_sep)

        if self.record_type_func:
            record_type = self.record_type_func(record_line)
            if record_type not in self.fields:
                if self.skip_unknown_types:
                    return None
                else:
                    raise FixedLengthUnknownRecordTypeError(record_type)
            field_length_sequence = self.fields[record_type]
        else:
            field_length_sequence = self.fields

        if isinstance(field_length_sequence, OrderedDict):
            field_length_sequence = iteritems(field_length_sequence)

        for field, field_length in field_length_sequence:
            # Check that fields are separated correctly
            if pointer and field_sep_len:
                if record_line[pointer:pointer + field_sep_len] != field_sep:
                    raise FixedLengthSeparatorError(field, pointer)
                pointer += field_sep_len

            value = record_line[pointer:pointer + field_length]
            # Check that the field is empty or doesn't start with a space
            if not field_sep_len:
                if self._invalid_just(field, value):
                    override = self.override_justification_error_func(field, value)
                    if override is None:
                        raise FixedLengthJustificationError(field, value)
                    else:
                        value = override
            if self.encoding is not None:
                value = value.decode(self.encoding)
            record[field] = value.strip() if self.strip else value
            pointer += field_length

        return record

    def _invalid_just(self, field, value):
        """ Returns True if the value is not justified correctly """
        if field in self.skip_justified:
            return False
        if field in self.right_justified:
            value = value.lstrip()[-1:]
        else:
            value = value.rstrip()[:1]
        return value.isspace()

    @classmethod
    def generate_type_from_offset_func(cls, position, length):
        """ Returns a function suitable for the record_type_func parameter """
        def get_record_type(record_line):
            return record_line[position:position + length]
        return get_record_type
