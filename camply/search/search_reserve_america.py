"""
Search Implementation: ReserveAmerica & Colorado State Parks
"""

import logging
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from dateutil.relativedelta import relativedelta

from camply.containers import AvailableCampsite, RecreationArea, SearchWindow
from camply.containers.data_containers import ListedCampsite
from camply.providers.reserve_america import (
    ColoradoStateParks,
    LarimerCounty,
    ReserveAmerica,
)
from camply.search.base_search import BaseCampingSearch
from camply.utils import logging_utils, make_list
from camply.utils.logging_utils import format_log_string, log_sorted_response

logger = logging.getLogger(__name__)


class SearchReserveAmerica(BaseCampingSearch):
    """
    Searches on ReserveAmerica.com for Campsites
    """

    provider_class: Type[ReserveAmerica] = ReserveAmerica

    def __init__(
        self,
        search_window: Union[SearchWindow, List[SearchWindow]],
        recreation_area: Optional[Union[List[int], int]] = None,
        weekends_only: bool = False,
        campgrounds: Optional[Union[List[Union[int, str]], int, str]] = None,
        nights: int = 1,
        equipment: Optional[List[Tuple[str, Optional[int]]]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize with Search Parameters
        """
        super().__init__(
            search_window=search_window,
            weekends_only=weekends_only,
            nights=nights,
            **kwargs,
        )
        self._recreation_area_ids: List[int] = (
            make_list(recreation_area, coerce=int) if recreation_area else []
        )
        self._campground_ids: List[int] = (
            make_list(campgrounds, coerce=int) if campgrounds else []
        )
        self.equipment = equipment
        campsites = make_list(kwargs.get("campsites", []), coerce=int) or []
        if len(campsites) > 0:
            self.campsite_finder.validate_campsites(
                campsites=campsites, facility_ids=self._campground_ids
            )
        if not self._campground_ids and not self._recreation_area_ids:
            logger.error(
                f"You must provide a Campground ID or a Recreation Area ID to {self.provider_class.__name__}"
            )
            sys.exit(1)

        if self._campground_ids:
            self.campgrounds = self.campsite_finder.find_campgrounds(
                campground_id=self._campground_ids,
                verbose=False,
            )
        else:
            self.campgrounds = self.campsite_finder.find_campgrounds(
                rec_area_id=self._recreation_area_ids,
                verbose=False,
            )
        self.campground_ids = [int(item.facility_id) for item in self.campgrounds]
        if len(self.campground_ids) == 0:
            logger.error("No Campgrounds Found Matching Your Search Criteria")
            sys.exit(1)

    def get_all_campsites(self, **kwargs: Dict[str, Any]) -> List[AvailableCampsite]:
        """
        Retrieve All Matching Campsites from the ReserveAmerica API
        """
        logger.info(f"Searching across {len(self.campgrounds)} campgrounds")
        for campground in self.campgrounds:
            log_str = format_log_string(campground)
            logger.info("    %s", log_str)

        campsites_found: List[AvailableCampsite] = []
        for month in self.search_months:
            for campground in self.campgrounds:
                logger.info(
                    f"Searching {campground.facility_name}, {campground.recreation_area} "
                    f"({campground.facility_id}) for availability: "
                    f"{month.strftime('%B, %Y')}"
                )
                end_date = month + relativedelta(months=1) - timedelta(days=1)
                campsites = self.campsite_finder.get_campsites(
                    campground_id=int(campground.facility_id),
                    start_date=month,
                    end_date=end_date,
                    search_days=self.search_days,
                    equipment=self.equipment,
                )
                logger.info(
                    f"\t{logging_utils.get_emoji(campsites)}\t"
                    f"{len(campsites)} total sites found in month of "
                    f"{month.strftime('%B')}"
                )
                campsites_found += campsites

        campsite_df = self.campsites_to_df(campsites=campsites_found)
        campsite_df_validated = self._filter_date_overlap(campsites=campsite_df)
        consolidated_campsites = self._consolidate_campsites(
            campsite_df=campsite_df_validated, nights=self.nights
        )
        compiled_campsites = self.df_to_campsites(campsite_df=consolidated_campsites)
        return compiled_campsites

    @classmethod
    def find_recreation_areas(
        cls, search_string: Optional[str] = None, **kwargs: Any
    ) -> List[RecreationArea]:
        """
        Return the ReserveAmerica Recreation Areas
        """
        rec_areas = cls.provider_class().search_for_recreation_areas(
            query=search_string, state=kwargs.get("state")
        )
        logger.info(f"{len(rec_areas)} Matching Recreation Areas Found")
        log_sorted_response(rec_areas)
        return rec_areas

    def list_campsite_units(self) -> List[ListedCampsite]:
        """
        List Campsite Units in Selected Campgrounds
        """
        logged_campsites: List[ListedCampsite] = []
        for facility_id in self.campground_ids:
            records = self.campsite_finder.get_campsites_per_facility(
                facility_id=facility_id
            )
            for item in records:
                logged_campsites.append(
                    ListedCampsite(
                        id=item.id,
                        name=f"{item.name} ({item.details.loopName or 'N/A'})",
                        facility_id=facility_id,
                    )
                )
        self.log_listed_campsites(
            campsites=logged_campsites,
            facilities=self.campgrounds,
        )
        return logged_campsites


class SearchColoradoStateParks(SearchReserveAmerica):
    """
    Searches on ReserveAmerica / CPW for Colorado State Parks Campsites
    """

    provider_class = ColoradoStateParks


class SearchLarimerCounty(SearchReserveAmerica):
    """
    Searches on larimercamping.com / ReserveAmerica for Larimer County Campsites
    """

    provider_class = LarimerCounty
