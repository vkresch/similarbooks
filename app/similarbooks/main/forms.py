from flask_wtf import FlaskForm
import datetime
from wtforms import (
    StringField,
    IntegerField,
    FloatField,
    SubmitField,
    SelectField,
    TextAreaField,
    DecimalRangeField,
    IntegerRangeField,
)
from wtforms.validators import DataRequired, NumberRange, Length
from wtforms.widgets import TextArea


class LandingSearchForm(FlaskForm):
    title = StringField(
        "Title",
        validators=[DataRequired()],
        render_kw={"placeholder": "Enter a title to search for books"},
    )
    submit = SubmitField("Search")
