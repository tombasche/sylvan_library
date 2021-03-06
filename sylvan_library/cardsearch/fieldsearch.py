from cardsearch.card_search import CardSearch
from cardsearch.parameters import *

import logging

logger = logging.getLogger('django')


class FieldSearch:

    def __init__(self):
        self.card_name = None
        self.rules_text = None
        self.cmc = None
        self.cmc_operator = None

        self.colours = []
        self.colour_identities = []

        self.exclude_unselected_colours = False
        self.match_colours_exactly = False
        self.exclude_unselected_colour_identities = False
        self.match_colour_identities_exactly = False

    def get_query(self):

        searcher = CardSearch()
        root_param = searcher.root_parameter

        if self.card_name:
            logger.info(f'Searching for card name {self.card_name}')
            root_param.add_parameter(CardNameParam(self.card_name))

        if self.rules_text:
            logger.info(f'Searching for rules text {self.rules_text}')
            root_param.add_parameter(CardRulesTextParam(self.rules_text))

        if self.cmc is not None:
            logger.info(f'Searching for CMC {self.cmc}/{self.cmc_operator}')
            root_param.add_parameter(CardCmcParam(self.cmc, self.cmc_operator))

        if self.colours:
            if self.match_colours_exactly:
                colour_root = root_param
            else:
                colour_root = OrParam()
                root_param.add_parameter(colour_root)

            for colour in self.colours:
                colour_root.add_parameter(CardColourParam(colour))

            if self.exclude_unselected_colours:
                exclude_param = NotParam()
                root_param.add_parameter(exclude_param)
                for colour in [c for c in Card.colour_flags.values() if c not in self.colours]:
                    p = CardColourParam(colour)
                    exclude_param.add_parameter(p)

        if self.colour_identities:
            if self.match_colour_identities_exactly:
                colour_id_root = root_param
            else:
                colour_id_root = OrParam()
                root_param.add_parameter(colour_id_root)

            for colour in self.colour_identities:
                colour_id_root.add_parameter(CardColourIdentityParam(colour))

            if self.exclude_unselected_colour_identities:
                exclude_param = NotParam()
                root_param.add_parameter(exclude_param)
                for colour in [c for c in Card.colour_flags.values() if c not in self.colour_identities]:
                    p = CardColourIdentityParam(colour)
                    exclude_param.add_parameter(p)

        return searcher.result_search()
