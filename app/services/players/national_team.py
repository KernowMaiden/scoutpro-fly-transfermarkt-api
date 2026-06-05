from dataclasses import dataclass

from app.services.base import TransfermarktBase
from app.utils.utils import extract_from_url
from app.utils.xpath import Players


@dataclass
class TransfermarktPlayerNationalTeam(TransfermarktBase):
    """
    Represents a service for retrieving a football player's national-team career on Transfermarkt.

    Transfermarkt does not expose caps/national-team data on the player profile or stats
    endpoints, but the dedicated national-team page surfaces the player's current (or former)
    national team plus their senior caps and goals in the page data-header.

    Args:
        player_id (str): The unique identifier of the player.

    Attributes:
        URL (str): The URL to fetch the player's national-team page.
    """

    player_id: str = None
    URL: str = "https://www.transfermarkt.com/-/nationalmannschaft/spieler/{player_id}"

    def __post_init__(self) -> None:
        """Initialize the TransfermarktPlayerNationalTeam class."""
        self.URL = self.URL.format(player_id=self.player_id)
        self.page = self.request_url_page()
        # A non-international player still renders a valid page (same player shell),
        # so we only guard against an invalid player id, not a missing NT section.
        self.raise_exception_if_not_found(xpath=Players.Profile.URL)

    def get_player_national_team(self) -> dict:
        """
        Retrieve and parse the player's national-team information: the national team they
        represent (current or former), their senior caps and goals, and the national team's
        Transfermarkt id. Returns nulls (and isInternational=False) when the player has no
        recorded international career.

        Returns:
            dict: A dictionary with the player's id, national team, caps/goals, and the
                timestamp of when the data was last updated.
        """
        label = self.get_text_by_xpath(Players.NationalTeam.INTL_LABEL)
        team_name = self.get_text_by_xpath(Players.NationalTeam.TEAM_NAME)
        team_url = self.get_text_by_xpath(Players.NationalTeam.TEAM_URL)
        caps_goals = self.get_list_by_xpath(Players.NationalTeam.CAPS_GOALS)

        caps = caps_goals[0] if len(caps_goals) >= 1 else None
        goals = caps_goals[1] if len(caps_goals) >= 2 else None

        self.response["id"] = self.player_id
        self.response["isInternational"] = team_name is not None
        self.response["isFormer"] = bool(label and "Former" in label)
        self.response["nationalTeam"] = team_name
        self.response["nationalTeamId"] = extract_from_url(team_url) if team_url else None
        # caps has no base validator -> coerce here; goals is coerced by the base int validator.
        self.response["caps"] = int(caps) if (caps and str(caps).strip().isdigit()) else None
        self.response["goals"] = goals

        return self.response
