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
    category = SelectField(
        "Kategorie",
        choices=[
            ("main.wohnung_kaufen", "Wohnung kaufen"),
            ("main.wohnung_mieten", "Wohnung mieten"),
            ("main.haus_kaufen", "Haus kaufen"),
            ("main.haus_mieten", "Haus mieten"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Suchen")


class PropertyForm(FlaskForm):
    typ = SelectField(
        "Kategorie",
        choices=[("wohnung", "Wohnung"), ("haus", "Haus")],
        validators=[DataRequired()],
    )
    street = StringField("Straße", validators=[DataRequired()])
    postcode = IntegerField("Postleitzahl", validators=[DataRequired()])
    square_meters = FloatField(
        "Quadratmeter", validators=[DataRequired(), NumberRange(min=0)]
    )
    rooms = FloatField("Zimmer", validators=[DataRequired(), NumberRange(min=0)])
    year_of_construction = IntegerField(
        "Baujahr", validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField("Bewerten")


class BMUForm(FlaskForm):
    square_meter = DecimalRangeField(
        "Area",
        default=50,
        validators=[NumberRange(min=5, max=100)],
        render_kw={"placeholder": "Square meters"},
    )
    rooms = IntegerRangeField(
        "Rooms",
        default=2,
        validators=[NumberRange(min=1, max=10)],
        render_kw={"placeholder": "Rooms"},
    )
    floor_number = IntegerRangeField(
        "Floor Number",
        default=1,
        validators=[NumberRange(min=0, max=10)],
        render_kw={"placeholder": "Floor number"},
    )
    energy_consumption = DecimalRangeField(
        "Energy",
        default=55,
        validators=[NumberRange(min=0, max=400)],
        render_kw={"placeholder": "Energy consumption"},
    )
    year_of_construction = IntegerRangeField(
        "Year",
        default=2000,
        validators=[
            NumberRange(
                min=1500, max=int(datetime.datetime.now().date().strftime("%Y"))
            )
        ],
        render_kw={"placeholder": "Year of construction"},
    )
    zip_code = IntegerField("ZIP Code", render_kw={"placeholder": "ZIP code"})
    submit_bmu = SubmitField("Calculate")


class CashFlowForm(FlaskForm):
    equity_capital = IntegerField(
        "Equity capital",
        default=25_000,
        validators=[NumberRange(min=0)],
    )
    repayment_rate = DecimalRangeField(
        "Repayment Rate",
        default=2.0,
        validators=[NumberRange(min=0, max=5.0)],
    )
    interest = DecimalRangeField(
        "Interest Rate",
        default=3.57,
        validators=[NumberRange(min=0, max=5.0)],
    )
    maintenance_price_rate_owner = DecimalRangeField(
        "Maintenance Rate",
        default=25.0,
        validators=[NumberRange(min=0, max=100)],
    )
    tax_rate = DecimalRangeField(
        "Tax Rate",
        default=40.0,
        validators=[NumberRange(min=0, max=100)],
    )
    submit_cashflow = SubmitField("Calculate")


class FeedbackForm(FlaskForm):
    feedback = TextAreaField(
        "", widget=TextArea(), validators=[DataRequired(), Length(max=5000)]
    )
    submit = SubmitField("Submit")


class FilterForm(FlaskForm):
    square_meter_filter_max = DecimalRangeField(
        "Square Meter",
        default=50.0,
        validators=[NumberRange(min=0, max=100)],
    )
    square_meter_filter_min = DecimalRangeField(
        "Square Meter",
        default=50.0,
        validators=[NumberRange(min=0, max=100)],
    )
    cashflow_min = DecimalRangeField(
        "Cash flow",
        default=0.0,
        validators=[NumberRange(min=-500, max=1000)],
    )
    submit_filter = SubmitField("Filter")
