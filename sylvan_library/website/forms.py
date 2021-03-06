from django import forms
from cardsearch import parameters


class SearchForm(forms.Form):
    card_name = forms.CharField(required=False)
    rules_text = forms.CharField(required=False)
    cmc = forms.IntegerField(required=False)
    cmc_operator = forms.ChoiceField(parameters.NUMERICAL_OPERATOR_CHOICES, required=False)

    exclude_colours = forms.BooleanField(required=False)
    match_colours = forms.BooleanField(required=False)

    exclude_colours_identity = forms.BooleanField(required=False)
    match_colours_identity = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        for colour, symbol in self.colour_list().items():
            self.fields['colour_' + colour] = forms.BooleanField(required=False)
            self.fields['colourid_' + colour] = forms.BooleanField(required=False)

    def colour_list(self):
        return {
            'white': 'w',
            'blue': 'u',
            'black': 'b',
            'red': 'r',
            'green': 'g',
            'colourless': 'c'
        }

    def colour_fields(self):
        for colour, symbol in self.colour_list().items():
            yield {'field': self['colour_' + colour], 'symbol': symbol}

    def colour_identity_fields(self):
        for colour, symbol in self.colour_list().items():
            yield {'field': self['colourid_' + colour], 'symbol': symbol}
