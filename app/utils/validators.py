from werkzeug.datastructures import ImmutableMultiDict
from app.utils.exceptions import MissingFieldsError

def validate_form_data(form_data: ImmutableMultiDict[str, str]):
    missing_fields = []
    required_fields = ['owner', 'repository', 'title']

    for field in required_fields:
        value = form_data.get(field)
        if not value:
            missing_fields.append(field)

    if missing_fields:
        raise MissingFieldsError(missing_fields)
