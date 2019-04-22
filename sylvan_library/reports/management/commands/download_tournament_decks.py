"""
Module for the verify_database command
"""

import os
import re
import json
import time
from datetime import datetime
from typing import List, Set
import requests

from django.core.management.base import BaseCommand
from django.db import transaction
from bs4 import BeautifulSoup

from cards.models import (
    Card,
    Deck,
    DeckCard,
    User,
)


class Command(BaseCommand):
    """
    THe command for downloading major tournament decks from MTGTop8
    """
    help = 'Downloads tournament decks from MTGTop8'

    deck_owner_username = 'MTGTOP8_TOURNAMENT_DECK_OWNER'

    def __init__(self):
        self.base_uri = 'https://www.mtgtop8.com/'
        self.output_path = os.path.join('reports', 'output', 'parsed_decks.json')
        if not os.path.exists(self.output_path):
            with open(self.output_path, 'w') as json_file:
                json.dump({'decks': [], 'events': []}, json_file)

        with open(self.output_path) as json_file:
            json_data = json.load(json_file)
            self.parsed_deck_uris = json_data['decks']
            self.parsed_event_uris = json_data['events']

        try:
            self.deck_user = User.objects.get(username=Command.deck_owner_username)
        except User.DoesNotExist:
            self.deck_user = User.objects.create(username=Command.deck_owner_username,
                                                 is_active=False)

        super().__init__()

    def handle(self, *args, **options) -> None:
        worlds_uri = 'format?f=ST&meta=97'
        pro_tour_uri = 'format?f=ST&meta=91'
        grand_prix_uri = 'format?f=ST&meta=96'
        for uri in [worlds_uri, pro_tour_uri, grand_prix_uri]:
            self.parse_event_summary(self.base_uri + uri)

    def parse_event_summary(self, event_summary_uri: str) -> None:
        """
        Parses an event summary page (which contains a list of events)
        :param event_summary_uri: The URI of the event summary page
        """
        visited_pages = set()
        pages_to_visit = {1}
        while pages_to_visit:
            page = pages_to_visit.pop()
            visited_pages.add(page)
            print(f'Parsing event list {event_summary_uri} on page{page}')
            resp = requests.post(event_summary_uri, {'cp': page})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, features='html.parser')
            pages_to_visit.update(self.find_event_summary_pages(soup, visited_pages))
            event_list = soup.select('table.Stable')[2]
            event_trs = event_list.find_all('tr', class_='hover_tr')
            for event in event_trs:
                link = event.find('a')
                href = link.attrs['href']
                self.parse_event(self.base_uri + href)

    # pylint: disable=no-self-use
    def find_event_summary_pages(self, soup: BeautifulSoup, visited_pages: Set[int]) -> List[int]:
        """
        Finds the page numbers of the event type that haven't been parsed yet
        :param soup: THe page soup to parse
        :param visited_pages: Pages that have already been visited
        :return: A list of pages to visit
        """
        nav_buttons = soup.select('form[name="format_form"] .Nav_norm')
        for button in nav_buttons:
            button_page = int(button.text)
            if button_page not in visited_pages:
                yield button_page

    def parse_event(self, event_uri: str) -> None:
        """
        Parses a single event (a tournament at a specific date with usually 8 decks)
        :param event_uri: The URI of te event page
        """
        if event_uri in self.parsed_event_uris:
            print(f'Skipping event {event_uri}')
            return

        print(f'Parsing event {event_uri}')
        resp = requests.get(event_uri)
        resp.raise_for_status()

        # The event page will default to the winning deck, so the page can be parsed as a deck
        self.parse_deck(event_uri)

        soup = BeautifulSoup(resp.text)
        deck_links = soup.select('div.hover_tr div.S14 a')
        for link in deck_links:
            href = link.attrs['href']
            self.parse_deck(self.base_uri + 'event' + href)

        self.parsed_event_uris.append(event_uri)
        self.write_parsed_decks_to_file()
        time.sleep(1)

    def parse_deck(self, deck_uri: str) -> None:
        """
        Parses a single deck URI, creating a new Deck object
        :param deck_uri: The URI of the deck
        """
        if deck_uri in self.parsed_deck_uris:
            print(f'Skipping deck {deck_uri}')
            return

        print(f'Parsing deck {deck_uri}')

        resp = requests.get(deck_uri)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text)
        deck_table = soup.select('table.Stable')[1]
        tables = deck_table.find_all('table')
        with transaction.atomic():
            deck = Deck()
            deck.owner = self.deck_user
            deck.name = soup.select_one('div.w_title').text
            deck.name = re.sub(r'\s+', ' ', deck.name).strip()

            summary = soup.select_one('td.S14')
            date_match = re.search(r'(?P<date>\d+/\d+/\d+)', summary.text)
            if not date_match:
                raise Exception('Could not find the date')
            deck.date_created = deck.last_modified = \
                datetime.strptime(date_match['date'], '%d/%m/%y')
            deck.save()

            for table in tables:
                card_rows = table.select('td.G14')
                for card_row in card_rows:
                    self.parse_deck_card(card_row.text, deck)

        self.parsed_deck_uris.append(deck_uri)
        self.write_parsed_decks_to_file()
        time.sleep(1)

    @staticmethod
    def parse_deck_card(row_text: str, deck: Deck) -> None:
        """
        Parses a row of card text and adds it to the given deck
        :param row_text: The row of card text
        :param deck: The deck to add the card to
        :return: The created DeckCard
        """
        matches = re.match(r'(?P<count>\d+) +(?P<name>.+)', row_text)
        if not matches:
            raise Exception(f'Could not parse {row_text}')

        print(matches['count'] + ' x ' + matches['name'])
        if matches['name'] == 'Unknown Card':
            return
        deck_card = DeckCard()
        deck_card.deck = deck
        deck_card.count = int(matches['count'])
        try:
            card = Card.objects.get(name=matches['name'], is_token=False)
        except Card.DoesNotExist:
            print(f"Couldn't find card {matches['name']}. Testing split card")
            first_name = matches['name'].split('/')[0].strip()
            card = Card.objects.get(name=first_name)

        deck_card.card = card
        deck_card.save()

    def write_parsed_decks_to_file(self) -> None:
        """
        WRite out the list of decks and events that have already been parsed to file
        (this is performed periodically so that decks aren't duplicated if an error occurred.
        """
        with open(self.output_path, 'w') as json_file:
            json.dump({'decks': self.parsed_deck_uris,
                       'events': self.parsed_event_uris}, json_file)
