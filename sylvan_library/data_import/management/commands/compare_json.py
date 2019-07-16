"""
Module for the update_database command
"""
import logging
import time
import datetime
from typing import List, Optional, Dict, Tuple
from django.db import transaction

from django.core.management.base import BaseCommand
from cards.models import (
    Block,
    Card,
    CardLegality,
    CardPrinting,
    CardPrintingLanguage,
    CardRuling,
    Colour,
    Language,
    PhysicalCard,
    Rarity,
    Set,
)
from data_import.importers import JsonImporter
from data_import.management.data_import_command import DataImportCommand

# from data_import.staging import StagedCard, StagedSet
import os
import _paths
import json
from datetime import date

logger = logging.getLogger("django")


class StagedCard:
    def __init__(self, json_data: dict, is_token: bool):
        self.is_token = is_token

        self.colour_identity = json_data.get("colourIdentity", [])
        self.colours = json_data.get("colors", [])
        self.cmc = json_data.get("convertedManaCost", 0)
        self.layout = json_data.get("layout")
        self.cost = json_data.get("maaaCost")
        self.name = json_data.get("name")
        self.power = json_data.get("number")
        self.scryfall_oracle_id = json_data.get("scryfallOracleId")
        self.rules_text = json_data.get("text")
        self.toughness = json_data.get("toughness")

        self.type = None
        if self.is_token:
            if "type" in json_data:
                self.type = json_data["type"].split("—")[0].strip()
        elif "types" in json_data:
            self.type = " ".join(
                (json_data.get("supertypes") or []) + (json_data["types"])
            )

        self.subtype = None
        if self.is_token:
            if "type" in json_data:
                self.subtype = json_data["type"].split("—")[-1].strip()
        elif "subtypes" in json_data:
            self.subtype = " ".join(json_data.get("subtypes"))

        self.rulings = json_data.get("rulings", [])
        self.legalities = json_data.get("legalities")
        self.has_other_names = "names" in json_data
        self.other_names = (
            [n for n in json_data["names"] if n != self.name]
            if self.has_other_names
            else []
        )
        self.side = json_data.get("side")
        self.is_reserved = bool(json_data.get("isReserved", False))

    def to_dict(self) -> dict:
        return {
            "is_token": self.is_token,
            "colour_identity": self.colour_identity,
            "colours": self.colours,
            "cmc": self.cmc,
            "layout": self.layout,
            "cost": self.cost,
            "name": self.name,
            "power": self.power,
            "scryfall_oracle_id": self.scryfall_oracle_id,
            "rules_text": self.rules_text,
            "toughness": self.toughness,
            "type": self.type,
            "subtype": self.subtype,
            "side": self.side,
            "is_reserved": self.is_reserved,
        }


class StagedSet:
    def __init__(self, set_data: dict):
        self.base_set_size = set_data["baseSetSize"]
        self.block = set_data.get("block")
        self.code = set_data["code"]
        self.is_foil_only = set_data["isFoilOnly"]
        self.is_online_only = set_data["isOnlineOnly"]
        self.keyrune_code = set_data["keyruneCode"]
        self.mcm_id = set_data.get("mcmId")
        self.mcm_name = set_data.get("mcmName")
        self.mtg_code = set_data.get("mtgoCode")
        self.name = set_data["name"]
        self.release_date = set_data["releaseDate"]
        self.tcg_player_group_id = set_data.get("tcg_player_group_id")
        self.total_set_size = set_data["totalSetSize"]
        self.type = set_data["type"]

    def to_dict(self) -> dict:
        return {
            "base_set_size": self.base_set_size,
            "block": self.block,
            "code": self.code,
            "is_foil_only": self.is_foil_only,
            "is_online_only": self.is_online_only,
            "keyrune_code": self.keyrune_code,
            "mcm_id": self.mcm_id,
            "mcm_name": self.mcm_name,
            "name": self.name,
            "release_date": self.release_date,
            "tcg_player_group_id": self.tcg_player_group_id,
            "total_set_size": self.total_set_size,
            "type": self.type,
        }


class StagedCardPrinting:
    def __init__(self, card_name: str, json_data: dict, set_data: dict):
        self.card_name = card_name

        self.artist = json_data.get("artist")
        self.border_colour = json_data.get("borderColor")
        self.frame_version = json_data.get("frameVersion")
        self.hasFoil = json_data.get("hasFoil")
        self.hasNonFoil = json_data.get("hasNonFoil")
        self.number = json_data.get("number")
        self.rarity = json_data.get("rarity")
        self.scryfall_id = json_data.get("scryfallId")
        self.scryfall_illustration_id = json_data.get("scryfallIllustrationId")
        self.uuid = json_data.get("uuid")
        self.multiverse_id = json_data.get("multiverseId")
        self.other_languages = json_data.get("foreignData")
        self.names = json_data.get("names", [])

        self.set_code = set_data["code"]

        self.is_new = False

    def to_dict(self):
        return {
            "card_name": self.card_name,
            "artist": self.artist,
            "border_colour": self.border_colour,
            "frame_version": self.frame_version,
            "hasfoil": self.hasFoil,
            "has_non_foil": self.hasNonFoil,
            "number": self.number,
            "rarity": self.rarity,
            "scryfall_id": self.scryfall_id,
            "scryfall_illustration_id": self.scryfall_illustration_id,
            "uuid": self.uuid,
            "multiverse_id": self.multiverse_id,
            "set_code": self.set_code,
        }


class StagedLegality:
    def __init__(self, card_name: str, format_code: str, restriction: str):
        self.card_name = card_name
        self.format_code = format_code
        self.restriction = restriction

    def to_dict(self) -> dict:
        return {
            "card_name": self.card_name,
            "format": self.format_code,
            "restriction": self.restriction,
        }


class StagedRuling:
    def __init__(self, card_name: str, text: str, ruling_date: str):
        self.card_name = card_name
        self.text = text
        self.ruling_date = ruling_date

    def to_dict(self) -> dict:
        return {
            "card_name": self.card_name,
            "text": self.text,
            "date": self.ruling_date,
        }


class StagedBlock:
    def __init__(self, name: str, release_date: date):
        self.name = name
        self.release_date = release_date

    def to_dict(self) -> dict:
        return {"name": self.name, "release_date": self.release_date}


class StagedCardPrintingLanguage:
    def __init__(
        self,
        staged_card_printing: StagedCardPrinting,
        foreign_data: dict,
        card_data: dict,
    ):
        self.printing_uuid = staged_card_printing.uuid

        self.language = foreign_data["language"]
        self.foreign_name = foreign_data["name"]

        self.multiverse_id = foreign_data.get("multiverseId")
        self.text = foreign_data.get("text")
        self.type = foreign_data.get("type")

        self.other_names = card_data.get("names", [])
        self.base_name = card_data["name"]
        if self.base_name in self.other_names:
            self.other_names.remove(self.base_name)
        self.layout = card_data["layout"]
        self.side = card_data.get("side")

        self.is_new = False
        self.has_physical_card = False

    def to_dict(self) -> dict:
        return {
            "printing_uid": self.printing_uuid,
            "language": self.language,
            "foreign_name": self.foreign_name,
            "multiverse_id": self.multiverse_id,
            "text": self.text,
            "type": self.type,
            "base_name": self.base_name,
        }


class StagedPhysicalCard:
    def __init__(self, printing_uuids: List[str], language_code: str, layout: str):
        self.printing_uids = printing_uuids
        self.language_code = language_code
        self.layout = layout

    def to_dict(self) -> dict:
        return {
            "printing_uids": self.printing_uids,
            "language": self.language_code,
            "layout": self.layout,
        }

    def __str__(self) -> str:
        return f"{'/'.join(self.printing_uids)} in {self.language_code} ({self.layout})"


class Command(BaseCommand):
    """
    The command for updating hte database
    """

    help = (
        "Uses the downloaded JSON files to update the database, "
        "including creating cards, set and rarities\n"
        "Use the update_rulings command to update rulings"
    )

    existing_cards = {}  # type: Dict[str, Card]
    existing_card_printings = {}  # type: Dict[str, CardPrinting]
    existing_sets = {}  # type: Dict[str, Set]
    existing_blocks = {}  # type: Dict[str, Block]
    existing_rulings = {}  # type: Dict[str, Dict[str, str]]
    existing_legalities = {}  # type: Dict[str, Dict[str, str]]

    cards_to_create = {}  # type: Dict[str, StagedCard]
    cards_to_update = {}  # type: Dict[str, Dict[str, Dict[str]]]
    cards_to_delete = set()

    cards_parsed = set()

    card_printings_to_create = {}  # type: Dict[str, StagedCardPrinting]
    card_printings_to_update = {}  # type: Dict[str, Dict[str,dict]]

    printed_languages_to_create = []  # type: List[StagedCardPrintingLanguage]
    physical_cards_to_create = []

    sets_to_create = {}  # type: Dict[str, StagedSet]
    sets_to_update = {}  # type: Dict[str, Dict[str, Dict[str]]]

    blocks_to_create = {}  # type: Dict[str, StagedBlock]

    rulings_to_create = []  # type: List[StagedRuling]
    rulings_to_delete = {}  # type: Dict[str, List[str]]
    cards_checked_For_rulings = set()  # type: Set

    cards_checked_for_legalities = set()  # type: Set
    legalities_to_create = []  # type: List[StagedLegality]
    legalities_to_delete = {}  # type: Dict[str, List[str]]
    legalities_to_update = {}  # type: Dict[str, Dict[str, Dict[str, str]]]

    card_links_to_create = {}  # type: Dict[str, List[str]]

    force_update = False
    start_time = None

    def add_arguments(self, parser):

        parser.add_argument(
            "--no-transaction",
            action="store_true",
            dest="no_transaction",
            default=False,
            help="Update the database without a transaction (unsafe)",
        )

    def handle(self, *args, **options):

        self.start_time = time.time()

        for card in Card.objects.filter(is_token=False):
            if card.name in self.existing_cards:
                raise Exception(f"Multiple cards with the same name found: {card.name}")
            self.existing_cards[card.name] = card

        self.existing_card_printings = {
            cp.json_id: cp
            for cp in CardPrinting.objects.prefetch_related(
                "printed_languages__language"
            ).all()
        }

        self.existing_sets = {s.code: s for s in Set.objects.all()}
        self.existing_blocks = {b.name: b for b in Block.objects.all()}
        for ruling in CardRuling.objects.select_related("card"):
            if ruling.card.name not in self.existing_rulings:
                self.existing_rulings[ruling.card.name] = {}
            self.existing_rulings[ruling.card.name][ruling.text] = ruling

        for legality in (
            CardLegality.objects.prefetch_related("card")
            .prefetch_related("format")
            .all()
        ):
            if legality.card.name not in self.existing_legalities:
                self.existing_legalities[legality.card.name] = {}
            self.existing_legalities[legality.card.name][
                legality.format.code
            ] = legality.restriction

        set_data_list = []

        for set_file_path in [
            os.path.join(_paths.SET_FOLDER, s) for s in os.listdir(_paths.SET_FOLDER)
        ]:
            if not set_file_path.endswith(".json"):
                continue

            with open(set_file_path, "r", encoding="utf8") as set_file:
                set_data = json.load(set_file, encoding="utf8")
                set_data_list.append(set_data)

        set_data_list.sort(key=lambda s: s.get("releaseDate") or str(date.max()))

        for set_data in set_data_list:
            self.parse_set_data(set_data)

        self.cards_to_delete = set(self.existing_cards.keys()).difference(
            self.cards_parsed
        )

        # print("\nCards to create:")
        # for card_name, staged_card in self.cards_to_create.items():
        #     print(card_name)
        #
        # print("\nCards to update:")
        # for card_name, differences in self.cards_to_update.items():
        #     print(f"{card_name}: {differences}")
        self.write_to_file()

        print(time.time() - self.start_time)

    def parse_set_data(self, set_data: dict) -> None:
        staged_set = StagedSet(set_data)
        if staged_set.code not in self.existing_sets:
            self.sets_to_create[staged_set.code] = staged_set
        else:
            existing_set = self.existing_sets[staged_set.code]
            differences = self.get_object_differences(
                existing_set,
                staged_set,
                [
                    # "base_set_size",
                    # "is_foil_only",
                    # "is_online_only",
                    "keyrune_code",
                    # "mcm_id",
                    # "mcm_name",
                    # "mtgo_code",
                    "name",
                    # "tcgplayer_group_id",
                    # "total_set_size",
                    "type",
                ],
            )
            if (not existing_set.block and staged_set.block) or (
                existing_set.block and existing_set.block.name != staged_set.block
            ):
                differences["block"] = {
                    "from": existing_set.block.name if existing_set.block else None,
                    "to": staged_set.block,
                }

            if (
                existing_set.release_date.strftime("%Y-%m-%d")
                != staged_set.release_date
            ):
                differences["release_date"] = {
                    "from": existing_set.release_date.strftime("%Y-%m-%d"),
                    "to": staged_set.release_date,
                }

            if differences:
                self.sets_to_update[staged_set.code] = differences

        if staged_set.block and staged_set.block not in self.existing_blocks:
            block_to_create = self.blocks_to_create.get(staged_set.block)
            if not block_to_create:
                self.blocks_to_create[staged_set.block] = StagedBlock(
                    staged_set.block, staged_set.release_date
                )
            else:
                block_to_create.release_date = min(
                    block_to_create.release_date, staged_set.release_date
                )

        self.process_physical_cards(set_data)
        self.process_card_links(set_data)

    def process_physical_cards(self, set_data: dict) -> None:
        new_printlangs = []
        for card_data in set_data.get("cards", []):
            staged_card = self.process_card(card_data, False)
            staged_printing, printlangs = self.process_card_printing(
                staged_card, set_data, card_data
            )

            for printlang in printlangs:
                if printlang.is_new:
                    new_printlangs.append(printlang)

        for new_printlang in new_printlangs:
            if new_printlang.has_physical_card or (
                new_printlang.layout == "meld" and new_printlang.side == "c"
            ):
                continue

            uids = []
            if new_printlang.other_names:

                for pl in new_printlangs:
                    if (
                        pl.base_name in new_printlang.other_names
                        and pl.language == new_printlang.language
                        and (
                            new_printlang.layout != "meld"
                            or new_printlang.side == "c"
                            or pl.side == "c"
                        )
                    ):
                        pl.has_physical_card = True
                        uids.append(pl.printing_uuid)
            uids.append(new_printlang.printing_uuid)

            staged_physical_card = StagedPhysicalCard(
                printing_uuids=uids,
                language_code=new_printlang.language,
                layout=new_printlang.layout,
            )
            self.physical_cards_to_create.append(staged_physical_card)
            new_printlang.has_physical_card = True

    def process_card(self, card_data: dict, is_token: bool) -> StagedCard:
        staged_card = StagedCard(card_data, is_token=is_token)
        if staged_card.name not in self.existing_cards:
            if staged_card.name not in self.cards_to_create:
                self.cards_to_create[staged_card.name] = staged_card
        elif staged_card.name not in self.cards_to_update:
            existing_card = self.existing_cards[staged_card.name]
            differences = self.get_card_differences(existing_card, staged_card)
            if differences:
                self.cards_to_update[staged_card.name] = differences

        self.process_card_rulings(staged_card)
        self.process_card_legalities(staged_card)
        self.cards_parsed.add(staged_card.name)
        return staged_card

    def process_card_rulings(self, staged_card: StagedCard) -> None:

        # If this card has already had its rulings parsed, than ignore it
        if staged_card.name in self.cards_checked_For_rulings:
            return

        self.cards_checked_For_rulings.add(staged_card.name)

        for ruling in staged_card.rulings:
            if (
                staged_card.name not in self.existing_rulings
                or ruling["text"] not in self.existing_rulings[staged_card.name]
            ):
                staged_ruling = StagedRuling(
                    staged_card.name, ruling["text"], ruling["date"]
                )
                self.rulings_to_create.append(staged_ruling)

        # For every existing ruling, it if isn't contained in the list of rulings,
        # then mark it for deletion
        if staged_card.name in self.existing_rulings:
            for existing_ruling, _ in self.existing_rulings[staged_card.name].items():
                if not any(
                    True
                    for ruling in staged_card.rulings
                    if ruling["text"] == existing_ruling
                ):
                    if staged_card.name not in self.rulings_to_delete:
                        self.rulings_to_delete[staged_card.name] = []

                    self.rulings_to_delete[staged_card.name].append(existing_ruling)

    def process_card_legalities(self, staged_card: StagedCard) -> None:
        if staged_card.name in self.cards_checked_for_legalities:
            return

        self.cards_checked_for_legalities.add(staged_card.name)

        for format, restriction in staged_card.legalities.items():
            if (
                staged_card.name not in self.existing_legalities
                or format not in self.existing_legalities[staged_card.name]
            ):
                staged_legality = StagedLegality(staged_card.name, format, restriction)
                self.legalities_to_create.append(staged_legality)

        if staged_card.name in self.existing_legalities:
            for old_format, old_restriction in self.existing_legalities[
                staged_card.name
            ].items():
                # Legalities to delete
                if old_format not in staged_card.legalities:
                    if staged_card.name not in self.legalities_to_delete:
                        self.legalities_to_delete[staged_card.name] = []
                    self.legalities_to_delete[staged_card.name].append(old_format)

                # Legalities to change
                elif staged_card.legalities[old_format] != old_restriction:
                    if staged_card.name not in self.legalities_to_update:
                        self.legalities_to_update[staged_card.name] = {}

                    self.legalities_to_update[staged_card.name][old_format] = {
                        "from": old_restriction,
                        "to": staged_card.legalities[old_format],
                    }

    def process_card_links(self, set_data: dict):
        for card in set_data.get("cards", []):
            if "names" not in card or not card["names"]:
                continue
            if card["name"] not in self.cards_to_create:
                continue

            staged_card = self.cards_to_create[card["name"]]
            for other_name in staged_card.other_names:
                if other_name not in self.cards_to_create:
                    continue
                other_staged_card = self.cards_to_create[other_name]
                if (
                    staged_card.layout == "meld"
                    and staged_card.side != "c"
                    and other_staged_card.layout != "c"
                ):
                    continue

                if staged_card.name not in self.card_links_to_create:
                    self.card_links_to_create[staged_card.name] = []

                self.card_links_to_create[staged_card.name].append(other_name)

    def get_object_differences(self, old_object, new_object, fields: List[str]) -> dict:
        result = {}
        for field in fields:
            old_val = getattr(old_object, field)
            new_val = getattr(new_object, field)
            if type(old_val) != type(new_val) and type(None) not in [
                type(old_val),
                type(new_val),
            ]:
                raise Exception(
                    f"Type mismatch for '{field}: {old_val} != {new_val} "
                    f"({type(old_val)} != {type(new_val)})"
                )

            if old_val != new_val:
                result[field] = {"from": old_val, "to": new_val}

        return result

    def get_set_differences(
        self, existing_set: Set, staged_set: StagedSet
    ) -> Dict[str, dict]:
        return self.get_object_differences(
            existing_set, staged_set, ["keyrune_code", "name", "total_set_size", "type"]
        )

    def get_card_differences(
        self, existing_card: Card, staged_card: StagedCard
    ) -> Dict[str, dict]:
        return self.get_object_differences(
            existing_card, staged_card, ["name", "rules_text", "type", "subtype"]
        )

    def get_card_printing_differences(
        self, existing_printing: CardPrinting, staged_printing: StagedCardPrinting
    ) -> Dict[str, dict]:
        """
        Gets the differences between an existing printing and one from the json

        Most of the time there won't be any differences, but this will be useful for adding in new
        fields that didn't exist before
        :param existing_printing:
        :param staged_printing:
        :return:
        """
        result = {}
        return result

    def process_card_printing(
        self, staged_card: StagedCard, set_data: dict, card_data: dict
    ) -> Tuple[StagedCardPrinting, List[StagedCardPrintingLanguage]]:
        staged_card_printing = StagedCardPrinting(staged_card.name, card_data, set_data)
        uuid = staged_card_printing.uuid
        if uuid not in self.existing_card_printings:
            if uuid not in self.card_printings_to_update:
                staged_card_printing.is_new = True
                self.card_printings_to_create[uuid] = staged_card_printing
            else:
                raise Exception(f"Printing already to be update {uuid}")
        elif uuid not in self.card_printings_to_update:
            existing_printing = self.existing_card_printings[uuid]
            differences = self.get_card_printing_differences(
                existing_printing, staged_card_printing
            )
            if differences:
                self.card_printings_to_update[uuid] = differences

        printlangs = [
            self.process_printed_language(
                staged_card_printing,
                {
                    "language": "English",
                    "multiverseId": staged_card_printing.multiverse_id,
                    "name": card_data["name"],
                    "text": card_data.get("text"),
                    "type": card_data.get("type"),
                },
                card_data,
            )
        ]

        for foreign_data in staged_card_printing.other_languages:
            staged_printlang = self.process_printed_language(
                staged_card_printing, foreign_data, card_data
            )
            printlangs.append(staged_printlang)

        return staged_card_printing, printlangs

    def process_printed_language(
        self,
        staged_card_printing: StagedCardPrinting,
        foreign_data: dict,
        card_data: dict,
    ) -> StagedCardPrintingLanguage:
        staged_card_printing_language = StagedCardPrintingLanguage(
            staged_card_printing, foreign_data, card_data
        )

        existing_print = self.get_existing_printed_language(
            staged_card_printing.uuid, staged_card_printing_language.language
        )

        if not existing_print:
            staged_card_printing_language.is_new = True
            self.printed_languages_to_create.append(staged_card_printing_language)

        return staged_card_printing_language

    def get_existing_printed_language(
        self, uuid: str, language: str
    ) -> Optional[CardPrintingLanguage]:
        existing_print = self.existing_card_printings.get(uuid)
        if not existing_print:
            return None

        for printlang in existing_print.printed_languages.all():
            if printlang.language.name == language:
                return printlang

        return None

    def write_object_to_json(self, filename: str, data: object) -> None:
        with open(filename, "w") as output_file:
            json.dump(data, output_file, indent=2)

    def write_to_file(self) -> None:
        self.write_object_to_json(
            _paths.BLOCKS_TO_CREATE_PATH,
            {
                block_name: staged_block.to_dict()
                for block_name, staged_block in self.blocks_to_create.items()
            },
        )

        self.write_object_to_json(
            _paths.SETS_TO_CREATE_PATH,
            {
                set_code: set_to_create.to_dict()
                for set_code, set_to_create in self.sets_to_create.items()
            },
        )

        self.write_object_to_json(
            _paths.SETS_TO_UPDATE_PATH,
            {
                set_code: set_to_update
                for set_code, set_to_update in self.sets_to_update.items()
            },
        )

        self.write_object_to_json(
            _paths.CARDS_TO_CREATE,
            {
                card_name: card_to_create.to_dict()
                for card_name, card_to_create in self.cards_to_create.items()
            },
        )

        self.write_object_to_json(
            _paths.CARDS_TO_UPDATE,
            {
                card_name: card_to_update
                for card_name, card_to_update in self.cards_to_update.items()
            },
        )

        self.write_object_to_json(_paths.CARDS_TO_DELETE, list(self.cards_to_delete))

        self.write_object_to_json(
            _paths.PRINTINGS_TO_CREATE,
            {
                uuid: printing_to_create.to_dict()
                for uuid, printing_to_create in self.card_printings_to_create.items()
            },
        )

        self.write_object_to_json(
            _paths.PRINTLANGS_TO_CREATE,
            [
                printlang_to_create.to_dict()
                for printlang_to_create in self.printed_languages_to_create
            ],
        )

        self.write_object_to_json(
            _paths.PHYSICAL_CARDS_TO_CREATE,
            [
                physical_card_to_create.to_dict()
                for physical_card_to_create in self.physical_cards_to_create
            ],
        )

        self.write_object_to_json(
            _paths.RULINGS_TO_CREATE,
            [ruling.to_dict() for ruling in self.rulings_to_create],
        )

        self.write_object_to_json(_paths.RULINGS_TO_DELETE, self.rulings_to_delete)

        self.write_object_to_json(
            _paths.LEGALITIES_TO_CREATE,
            [legality.to_dict() for legality in self.legalities_to_create],
        )

        self.write_object_to_json(
            _paths.LEGALITIES_TO_DELETE, self.legalities_to_delete
        )

        self.write_object_to_json(
            _paths.CARD_LINKS_TO_CREATE, self.card_links_to_create
        )
