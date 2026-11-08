"""
ReserveAmerica Provider Implementation
"""

import json
import logging
import os
import pathlib
import sys
import urllib.parse
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import ratelimit
import requests

from camply.config import FileConfig, ReserveAmericaConfig
from camply.containers import (
    AvailableCampsite,
    CampgroundFacility,
    CamplyModel,
    RecreationArea,
)
from camply.containers.base_container import RecDotGovAttribute
from camply.containers.data_containers import CampsiteLocation
from camply.containers.reserve_america import (
    ReserveAmericaAvailabilitySlice,
    ReserveAmericaCampsiteRecord,
    ReserveAmericaCampsiteResponse,
    ReserveAmericaRecord,
    ReserveAmericaSearchResponse,
)
from camply.exceptions import CamplyError
from camply.providers.base_provider import BaseProvider
from camply.utils.logging_utils import log_sorted_response

logger = logging.getLogger(__name__)


class ReserveAmericaError(CamplyError):
    """
    ReserveAmerica Provider Error
    """


class ReserveAmerica(BaseProvider):
    """
    Camply Provider for ReserveAmerica & State Park Systems (including Colorado CPW)
    """

    state_code: Optional[str] = ReserveAmericaConfig.DEFAULT_STATE
    contract_code: Optional[str] = None
    verifiable_only: bool = True
    booking_base_url: str = ReserveAmericaConfig.BASE_URL

    __offline_cache_dir__: Optional[pathlib.Path] = None

    def __init__(self) -> None:
        """
        Initialize ReserveAmerica Provider
        """
        super().__init__()
        self.session = requests.Session()
        self.headers = ReserveAmericaConfig.REQUEST_CLIENT_HEADER.copy()
        self.session.headers.update(self.headers)
        self.authenticated: bool = False
        self.auth_timestamp: Optional[datetime] = None

        self.reserveamerica_records: Dict[int, ReserveAmericaRecord] = {}
        self.reserveamerica_rec_areas: Dict[int, RecreationArea] = {}
        self.reserveamerica_campgrounds: Dict[int, CampgroundFacility] = {}
        self.reserveamerica_campsites: Dict[int, ReserveAmericaCampsiteRecord] = {}
        self.campsite_ids: List[int] = []
        self.metadata_refreshed: Set[str] = set()
        self.active_search: bool = False

    @property
    def offline_cache_dir(self) -> pathlib.Path:
        """
        Offline Cache Directory
        """
        if self.__offline_cache_dir__ is None:
            return FileConfig.RESERVE_AMERICA_PROVIDER / self.__class__.__name__
        return self.__offline_cache_dir__

    def authenticate(self, force: bool = False) -> None:
        """
        Obtain idToken and a1Data session tokens from ReserveAmerica /signin
        """
        if (
            not force
            and self.authenticated is True
            and self.auth_timestamp is not None
            and (datetime.now() - self.auth_timestamp) < timedelta(minutes=25)
        ):
            return

        id_token = os.getenv("RESERVE_AMERICA_ID_TOKEN")
        a1_data = os.getenv("RESERVE_AMERICA_A1_DATA")

        if not id_token or not a1_data:
            logger.debug(
                "Authenticating session via %s", ReserveAmericaConfig.SIGNIN_URL
            )
            auth_resp = self.session.get(
                ReserveAmericaConfig.SIGNIN_URL,
                headers=ReserveAmericaConfig.REQUEST_CLIENT_HEADER,
                timeout=30,
            )
            self._check_waf_block(response=auth_resp)
            auth_resp.raise_for_status()
            id_token = auth_resp.cookies.get("idToken")
            a1_data = auth_resp.cookies.get("a1Data")

        if not id_token or not a1_data:
            raise ReserveAmericaError(
                "Unable to retrieve idToken and a1Data authentication cookies from ReserveAmerica."
            )

        unquoted_a1 = urllib.parse.unquote(a1_data)
        self.session.cookies.update(
            {
                "idToken": id_token,
                "a1Data": a1_data,
                "Authorization": id_token,
                "A1Data": a1_data,
            }
        )
        self.session.headers.update(
            {
                "Authorization": id_token,
                "A1Data": unquoted_a1,
                **ReserveAmericaConfig.REQUEST_CLIENT_HEADER,
            }
        )
        self.authenticated = True
        self.auth_timestamp = datetime.now()

    @staticmethod
    def _check_waf_block(response: requests.Response) -> None:
        """
        Detect AWS WAF CAPTCHA gate and raise a clear error without attempting to bypass
        """
        waf_action = response.headers.get("x-amzn-waf-action", "")
        if waf_action.lower() == "captcha" or (
            response.status_code == 405 and "Human Verification" in response.text
        ):
            raise ReserveAmericaError(
                "ReserveAmerica API request was blocked by AWS WAF Human Verification (CAPTCHA)."
            )

    def get_booking_url(
        self,
        contract_code: str,
        facility_id: int,
        arrival_date: Optional[date] = None,
    ) -> str:
        """
        Generate the Booking URL for a ReserveAmerica / CPW Facility
        """
        record = self.reserveamerica_records.get(facility_id)
        if record and record.details.baseURL:
            base_path = record.details.baseURL
            if base_path.startswith("/"):
                url = f"{self.booking_base_url}{base_path}"
            else:
                url = base_path
        else:
            url = (
                f"{self.booking_base_url}/explore/campground"
                f"/{contract_code}/{facility_id}/overview"
            )
        if arrival_date is not None:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}arrivalDate={arrival_date.strftime(ReserveAmericaConfig.DATE_FORMAT)}"
        return url

    def _fetch_metadata_from_disk(
        self, file_path: pathlib.Path
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Read cached facility records from disk if less than 24 hours old
        """
        if not file_path.exists():
            return None
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        if (
            datetime.now() - modified_time > timedelta(days=1)
            and self.active_search is False
        ):
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))

    def refresh_metadata(self, state: Optional[str] = None) -> None:
        """
        Fetch and cache campground search records for the given state
        """
        target_state = (
            state or self.state_code or ReserveAmericaConfig.DEFAULT_STATE
        ).upper()
        if target_state in self.metadata_refreshed:
            return

        metadata_file = self.offline_cache_dir.joinpath(
            f"facilities_{target_state}.json"
        )
        raw_records = self._fetch_metadata_from_disk(file_path=metadata_file)

        if raw_records is None:
            self.authenticate()
            self.offline_cache_dir.mkdir(parents=True, exist_ok=True)
            all_records: List[Dict[str, Any]] = []
            page = 0
            while True:
                params = {
                    "stype": "state",
                    "tstc": target_state,
                    "rcp": page,
                }
                resp = self.session.get(
                    ReserveAmericaConfig.SEARCH_ENDPOINT,
                    params=params,
                    timeout=30,
                )
                self._check_waf_block(response=resp)
                resp.raise_for_status()
                parsed = ReserveAmericaSearchResponse(**resp.json())
                for rec in parsed.records:
                    all_records.append(rec.dict())
                if not parsed.records or parsed.control.currentPage >= (
                    parsed.totalPages - 1
                ):
                    break
                page += 1
            raw_records = all_records
            metadata_file.write_text(
                json.dumps(raw_records, indent=2), encoding="utf-8"
            )

        for rec_dict in raw_records:
            rec = ReserveAmericaRecord(**rec_dict)
            if self.verifiable_only and not rec.details.verifiableAvailability:
                continue
            if (
                self.contract_code is not None
                and rec.details.contrCode.upper() != self.contract_code.upper()
            ):
                continue
            if rec.details.dayUseOnly is True:
                continue

            self.reserveamerica_records[rec.id] = rec

            agency_id = 1
            agency_name = f"{target_state} State Parks"
            if (
                rec.details.affiliation
                and rec.details.affiliation.agencies
                and len(rec.details.affiliation.agencies) > 0
            ):
                first_agency = rec.details.affiliation.agencies[0]
                if first_agency.id is not None:
                    agency_id = first_agency.id
                if first_agency.name:
                    agency_name = first_agency.name

            if agency_id not in self.reserveamerica_rec_areas:
                self.reserveamerica_rec_areas[agency_id] = RecreationArea(
                    recreation_area=agency_name,
                    recreation_area_id=agency_id,
                    recreation_area_location=target_state,
                    description=f"{agency_name} ({target_state})",
                )

            coords = None
            if (
                rec.details.coordinates
                and rec.details.coordinates.latitude is not None
                and rec.details.coordinates.longitude is not None
            ):
                coords = (
                    rec.details.coordinates.latitude,
                    rec.details.coordinates.longitude,
                )

            self.reserveamerica_campgrounds[rec.id] = CampgroundFacility(
                facility_name=rec.name,
                facility_id=rec.id,
                recreation_area=agency_name,
                recreation_area_id=agency_id,
                coordinates=coords,
            )

        self.metadata_refreshed.add(target_state)

    def search_for_recreation_areas(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[RecreationArea]:
        """
        Retrieve Recreation Areas for ReserveAmerica / State Parks
        """
        if (
            self.state_code is not None
            and state is not None
            and state.upper() != self.state_code.upper()
            and self.__class__ is not ReserveAmerica
        ):
            raise CamplyError(
                f"{self.__class__.__name__} doesn't support states outside {self.state_code}"
            )
        target_state = state or self.state_code or ReserveAmericaConfig.DEFAULT_STATE
        self.refresh_metadata(state=target_state)
        rec_areas = list(self.reserveamerica_rec_areas.values())
        if query is not None:
            logger.info(f'Searching for Recreation Areas: "{query}"')
            rec_areas = [
                area
                for area in rec_areas
                if self._search_camply_model(query=query, model=area)
            ]
        return rec_areas

    def find_recreation_areas(
        self, search_string: Optional[str] = None, **kwargs: Any
    ) -> List[RecreationArea]:
        """
        Find and log Recreation Areas
        """
        rec_areas = self.search_for_recreation_areas(
            query=search_string, state=kwargs.get("state")
        )
        logger.info(f"{len(rec_areas)} Matching Recreation Areas Found")
        log_sorted_response(rec_areas)
        return rec_areas

    def find_campgrounds(
        self,
        search_string: Optional[str] = None,
        rec_area_id: Optional[List[int]] = None,
        state: Optional[str] = None,
        verbose: bool = True,
        campground_id: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> List[CampgroundFacility]:
        """
        Find Campgrounds matching search criteria
        """
        self.active_search = True
        if (
            self.state_code is not None
            and state is not None
            and state.upper() != self.state_code.upper()
            and self.__class__ is not ReserveAmerica
        ):
            raise CamplyError(
                f"{self.__class__.__name__} doesn't support states outside {self.state_code}"
            )
        campground_id = campground_id or []
        rec_area_id = rec_area_id or []
        target_state = state or self.state_code or ReserveAmericaConfig.DEFAULT_STATE

        if search_string is not None:
            logger.info(f'Searching for Campgrounds: "{search_string}"')

        self.refresh_metadata(state=target_state)
        found_campgrounds = self._search_for_campgrounds(
            campground_id=campground_id,
            rec_area_id=rec_area_id,
            search_string=search_string,
        )
        if verbose is True:
            logger.info(f"{len(found_campgrounds)} Matching Campgrounds Found")
            log_sorted_response(found_campgrounds)
        self.active_search = False
        return found_campgrounds

    def _search_for_campgrounds(
        self,
        campground_id: List[int],
        rec_area_id: List[int],
        search_string: Optional[str],
    ) -> List[CampgroundFacility]:
        """
        Filter loaded campgrounds by ID, recreation area ID, or search string
        """
        found_campgrounds: List[CampgroundFacility] = []
        if len(campground_id) >= 1:
            target_ids = {int(cid) for cid in campground_id}
            found_campgrounds = [
                cg
                for cg in self.reserveamerica_campgrounds.values()
                if int(cg.facility_id) in target_ids
            ]
        elif len(rec_area_id) >= 1:
            target_areas = {int(rid) for rid in rec_area_id}
            found_campgrounds = [
                cg
                for cg in self.reserveamerica_campgrounds.values()
                if int(cg.recreation_area_id) in target_areas
            ]
        elif search_string is not None:
            found_campgrounds = [
                cg
                for cg in self.reserveamerica_campgrounds.values()
                if self._search_camply_model(query=search_string, model=cg)
            ]
        else:
            found_campgrounds = list(self.reserveamerica_campgrounds.values())
        return found_campgrounds

    @classmethod
    def _search_camply_model(cls, query: str, model: CamplyModel) -> bool:
        """
        Case-insensitive substring match across model fields
        """
        return any(
            query.lower() in str(value).lower() for value in model.dict().values()
        )

    @ratelimit.sleep_and_retry
    @ratelimit.limits(calls=2, period=1)
    def get_campsites_response(
        self,
        campground_id: int,
        arrival_date: date,
        length_of_stay: int = 1,
        available_only: bool = True,
        equipment: Optional[List[Tuple[str, Optional[int]]]] = None,
    ) -> List[ReserveAmericaCampsiteRecord]:
        """
        Fetch all pages of campsite availability records from ReserveAmerica for a given arrival date
        """
        self.authenticate()
        record = self.reserveamerica_records.get(int(campground_id))
        contract_code = (
            record.details.contrCode
            if record is not None
            else (self.contract_code or ReserveAmericaConfig.DEFAULT_CONTRACT)
        )
        url = (
            f"{ReserveAmericaConfig.PRODUCTS_ENDPOINT}"
            f"/{contract_code}/{campground_id}/campsites"
        )

        extra_params: Dict[str, Any] = {}
        if equipment:
            for eq_name, eq_len in equipment:
                site_type_id = ReserveAmericaConfig.SITE_TYPE_MAPPING.get(
                    str(eq_name).lower()
                )
                if site_type_id is not None:
                    extra_params["pa99999"] = site_type_id
                if eq_len is not None:
                    try:
                        parsed_len = int(round(float(eq_len)))
                        if parsed_len > 0:
                            extra_params["pa109"] = parsed_len
                    except (ValueError, TypeError):
                        pass

        all_records: List[ReserveAmericaCampsiteRecord] = []
        page = 0
        while True:
            params: Dict[str, Any] = {
                "displayGISMap": "false",
                "rcp": page,
                "next": "true" if available_only else "false",
                "fc": "false",
                "arv": arrival_date.strftime(ReserveAmericaConfig.DATE_FORMAT),
                "lsy": length_of_stay,
                **extra_params,
            }
            resp = self.session.get(url, params=params, timeout=30)
            self._check_waf_block(response=resp)
            resp.raise_for_status()
            parsed = ReserveAmericaCampsiteResponse(**resp.json())
            all_records.extend(parsed.records)
            if not parsed.records or parsed.control.currentPage >= (
                parsed.totalPages - 1
            ):
                break
            page += 1
        return all_records

    def get_campsites(
        self,
        campground_id: int,
        start_date: Union[datetime, date],
        end_date: Union[datetime, date],
        search_days: Optional[List[date]] = None,
        equipment: Optional[List[Tuple[str, Optional[int]]]] = None,
    ) -> List[AvailableCampsite]:
        """
        Get Available Campsites for a campground across the requested dates
        """
        self.refresh_metadata()
        start_dt = (
            start_date.date() if isinstance(start_date, datetime) else start_date
        )
        end_dt = end_date.date() if isinstance(end_date, datetime) else end_date

        if search_days is not None:
            days_to_query = [
                d.date() if isinstance(d, datetime) else d
                for d in search_days
                if start_dt <= (d.date() if isinstance(d, datetime) else d) <= end_dt
            ]
        else:
            num_days = max((end_dt - start_dt).days, 1)
            days_to_query = [start_dt + timedelta(days=i) for i in range(num_days)]

        campsites: List[AvailableCampsite] = []
        for query_day in sorted(set(days_to_query)):
            if query_day < date.today():
                continue
            records = self.get_campsites_response(
                campground_id=campground_id,
                arrival_date=query_day,
                length_of_stay=1,
                available_only=True,
                equipment=equipment,
            )
            for unit in records:
                self.reserveamerica_campsites[unit.id] = unit
                if unit.available is not True or unit.bookingStatus != "AVAILABLE":
                    continue
                for grid_slice in unit.availabilityGrid:
                    if (
                        grid_slice.status == "AVAILABLE"
                        and grid_slice.date == query_day
                    ):
                        campsite = self._get_available_campsite(
                            availability_slice=grid_slice,
                            campground_id=campground_id,
                            unit=unit,
                        )
                        if (
                            len(self.campsite_ids) == 0
                            or int(campsite.campsite_id) in self.campsite_ids
                            or str(campsite.campsite_site_name)
                            in [str(cid) for cid in self.campsite_ids]
                        ):
                            campsites.append(campsite)
        return campsites

    def _get_available_campsite(
        self,
        availability_slice: ReserveAmericaAvailabilitySlice,
        campground_id: int,
        unit: ReserveAmericaCampsiteRecord,
    ) -> AvailableCampsite:
        """
        Convert a ReserveAmericaCampsiteRecord and AvailabilitySlice into an AvailableCampsite
        """
        start_dt = datetime.fromordinal(availability_slice.date.toordinal())
        facility = self.reserveamerica_campgrounds.get(int(campground_id))
        record = self.reserveamerica_records.get(int(campground_id))
        contract_code = (
            record.details.contrCode
            if record is not None
            else (self.contract_code or ReserveAmericaConfig.DEFAULT_CONTRACT)
        )

        if facility is None:
            facility = CampgroundFacility(
                facility_name=f"Campground #{campground_id}",
                facility_id=campground_id,
                recreation_area=f"{contract_code} State Parks",
                recreation_area_id=1,
            )

        booking_url = self.get_booking_url(
            contract_code=contract_code,
            facility_id=campground_id,
            arrival_date=availability_slice.date,
        )

        min_people = 1
        max_people = 1
        attributes_list: List[RecDotGovAttribute] = []
        lat: Optional[float] = (
            facility.coordinates[0] if facility.coordinates else None
        )
        lon: Optional[float] = (
            facility.coordinates[1] if facility.coordinates else None
        )

        if unit.details.categoriesAttributes:
            for cat in unit.details.categoriesAttributes:
                for attr in cat.attributes or []:
                    val_str = ", ".join(attr.displayValue or attr.value or [])
                    if attr.name:
                        attributes_list.append(
                            RecDotGovAttribute(
                                attribute_category=cat.categoryLabel,
                                attribute_id=attr.id or 0,
                                attribute_name=attr.name,
                                attribute_value=val_str,
                            )
                        )
                    if attr.id == 18 and attr.value:
                        try:
                            min_people = int(attr.value[0])
                        except ValueError:
                            pass
                    elif attr.id == 12 and attr.value:
                        try:
                            max_people = int(attr.value[0])
                        except ValueError:
                            pass
                    elif attr.id == 11059 and attr.value:
                        try:
                            lat = float(attr.value[0])
                        except ValueError:
                            pass
                    elif attr.id == 11060 and attr.value:
                        try:
                            lon = float(attr.value[0])
                        except ValueError:
                            pass

        use_type = (
            unit.prodInfo.typeOfUseLabel
            if unit.prodInfo and unit.prodInfo.typeOfUseLabel
            else "Overnight"
        )

        return AvailableCampsite(
            campsite_id=unit.id,
            booking_date=start_dt,
            booking_end_date=start_dt + timedelta(days=1),
            booking_nights=1,
            campsite_site_name=unit.name,
            campsite_loop_name=unit.details.loopName or "Default Loop",
            campsite_type=unit.prodGrpName,
            campsite_occupancy=(min_people, max_people),
            campsite_use_type=use_type,
            availability_status="Available",
            recreation_area=facility.recreation_area,
            recreation_area_id=facility.recreation_area_id,
            facility_name=facility.facility_name,
            facility_id=facility.facility_id,
            booking_url=booking_url,
            location=CampsiteLocation(latitude=lat, longitude=lon)
            if (lat is not None and lon is not None)
            else None,
            campsite_attributes=attributes_list or None,
        )

    def get_campsites_per_facility(
        self, facility_id: int
    ) -> List[ReserveAmericaCampsiteRecord]:
        """
        Get all campsites for a facility (used for listing and validating campsites)
        """
        records = self.get_campsites_response(
            campground_id=facility_id,
            arrival_date=date.today() + timedelta(days=1),
            length_of_stay=1,
            available_only=False,
        )
        for rec in records:
            self.reserveamerica_campsites[rec.id] = rec
        return records

    def validate_campsites(
        self, campsites: List[int], facility_ids: List[int]
    ) -> None:
        """
        Filter search to specific campsite IDs
        """
        for campsite_id in campsites:
            logger.info("Searching Specific campsite ID: %s", campsite_id)
        self.campsite_ids = [int(cid) for cid in campsites]


class ColoradoStateParks(ReserveAmerica):
    """
    Colorado State Parks (Colorado Parks and Wildlife / CPW via ReserveAmerica)
    """

    state_code = "CO"
    contract_code = "CO"
    verifiable_only = True


class LarimerCounty(ReserveAmerica):
    """
    Larimer County Parks (larimercamping.com via ReserveAmerica)
    """

    state_code = "CO"
    contract_code = ReserveAmericaConfig.LARIMER_CONTRACT
    verifiable_only = True
    booking_base_url = ReserveAmericaConfig.LARIMER_BASE_URL
