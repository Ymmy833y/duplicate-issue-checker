import pytest

from werkzeug.datastructures import ImmutableMultiDict

from app.utils.validators import validate_form_data
from app.utils.exceptions import MissingFieldsError

class TestValidateFormData:
    def test_success(self):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title'
        })

        try:
            validate_form_data(form_data)
        except MissingFieldsError:
            pytest.fail('Unexpected MissingFieldsError raised.')

    def test_missing_fields(self):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
        })
        with pytest.raises(MissingFieldsError) as excinfo:
            validate_form_data(form_data)

        assert excinfo.value.missing_fields == ['repository', 'title']
