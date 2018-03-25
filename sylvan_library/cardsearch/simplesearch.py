from cardsearch.card_search import CardSearch
from cardsearch.parameters import *
from cards.models import Colour


class SimpleSearch:

    def __init__(self):
        self.text = None
        self.colours = list()
        self.include_name = False
        self.include_types = False
        self.include_rules = False
        self.set = None
        self.format = None
        self.match_colours = False
        self.multicoloured_only = False
        self.exclude_colours = False
        self.card_type = False
        self.sort_order = None

    def get_query(self):

        searcher = CardSearch()
        root_param = searcher.root_parameter

        if self.text:
            text_root = root_param.add_parameter(OrParam())
            if self.include_name:
                text_root.add_parameter(CardNameParam(self.text))

            if self.include_rules:
                text_root.add_parameter(CardRulesTextParam(self.text))

            if self.include_types:
                text_root.add_parameter(CardTypeParam(self.text))
                text_root.add_parameter(CardSubtypeParam(self.text))

        if self.colours:
            param = AndParam() if self.match_colours else OrParam()
            root_param.add_parameter(param)

            for colour in self.colours:
                param.add_parameter(CardColourParam(colour))

            if self.exclude_colours:
                for colour in [c for c in Colour.objects.all() if c not in self.colours]:
                    p = CardColourParam(colour)
                    p.boolean_flag = False
                    root_param.add_parameter(p)

        if self.set:
            root_param.add_parameter(CardSetParam(self.set))

        if self.multicoloured_only:
            root_param.add_parameter(CardMulticolouredOnlyParam())

        if self.card_type:
            root_param.add_parameter(CardTypeParam(self.card_type))

        return searcher.result_search()
