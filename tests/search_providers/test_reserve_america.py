"""
ReserveAmerica & ColoradoStateParks Testing
"""

import datetime
import json
import pathlib
from unittest import mock

import pytest
import requests

from camply.containers import AvailableCampsite, SearchWindow
from camply.providers import ColoradoStateParks, LarimerCounty, ReserveAmerica
from camply.providers.reserve_america import ReserveAmericaError
from camply.search import (
    SearchColoradoStateParks,
    SearchLarimerCounty,
    SearchReserveAmerica,
)

SAMPLE_SEARCH_RESPONSE = {
    "totalRecords": 3,
    "totalPages": 1,
    "startIndex": 0,
    "endIndex": 2,
    "control": {"currentPage": 0, "pageSize": 20},
    "records": [
        {
            "type": "camping",
            "namingId": "CO_50022",
            "namingLabel": "Cherry Creek State Park",
            "id": 50022,
            "name": "Cherry Creek State Park",
            "targetItem": False,
            "matchingFilters": True,
            "reservableType": None,
            "available": False,
            "proximity": 0.0,
            "summary": None,
            "details": {
                "id": 50022,
                "contrCode": "CO",
                "stateCodes": ["CO"],
                "name": "Cherry Creek State Park",
                "baseURL": "/camping/cherry-creek-state-park/r/facilityDetails.do?contractCode=CO&parkId=50022",
                "imageURL": "/webphotos/CO/pid50022/0/180x120.jpg",
                "verifiableAvailability": True,
                "affiliation": {
                    "facilityID": 0,
                    "name": "",
                    "url": None,
                    "agencies": [
                        {
                            "id": 50001,
                            "code": "CPW",
                            "name": "Colorado Parks and Wildlife",
                        }
                    ],
                },
                "facilityTypes": ["camping"],
                "cta": {
                    "caption": "label_cta_check_availability",
                    "url": None,
                    "type": "REGULAR",
                },
                "dayUse": True,
                "dayUseOnly": False,
                "ratingSupport": False,
                "favoriteSupport": True,
                "favorite": False,
                "webAddress": "http://cpw.state.co.us/placestogo/Parks/cherrycreek",
                "coordinates": {
                    "latitude": 39.6286111,
                    "longitude": -104.8305556,
                },
                "hiddenOnMap": False,
                "crossOverCustomLanding": False,
                "legacyRequired": False,
                "lineOfBusinesses": ["CAMPING", "DAYUSE"],
                "nonClientFacility": False,
            },
        },
        {
            "type": "camping",
            "namingId": "LARC_710105",
            "namingLabel": "Horsetooth Reservoir",
            "id": 710105,
            "name": "Horsetooth Reservoir",
            "targetItem": False,
            "matchingFilters": True,
            "reservableType": None,
            "available": False,
            "proximity": 0.0,
            "summary": None,
            "details": {
                "id": 710105,
                "contrCode": "LARC",
                "stateCodes": ["CO"],
                "name": "Horsetooth Reservoir",
                "baseURL": "https://www.larimercamping.com/camping/horsetooth-reservoir/r/facilityDetails.do?contractCode=LARC&parkId=710105",
                "imageURL": "/webphotos/LARC/pid710105/0/180x120.jpg",
                "verifiableAvailability": True,
                "affiliation": {
                    "facilityID": 0,
                    "name": "",
                    "url": None,
                    "agencies": [
                        {
                            "id": 710003,
                            "code": "Larimer Agency",
                            "name": "Larimer County Agency",
                        }
                    ],
                },
                "facilityTypes": ["camping"],
                "dayUse": True,
                "dayUseOnly": False,
                "coordinates": {
                    "latitude": 40.5294444,
                    "longitude": -105.165,
                },
                "lineOfBusinesses": ["CAMPING", "DAYUSE"],
                "nonClientFacility": False,
            },
        },
        {
            "type": "camping",
            "namingId": "FLST_755487",
            "namingLabel": "ALDER GUARD STATION",
            "id": 755487,
            "name": "ALDER GUARD STATION",
            "targetItem": False,
            "matchingFilters": True,
            "available": False,
            "proximity": 0.0,
            "details": {
                "id": 755487,
                "contrCode": "FLST",
                "stateCodes": ["CO"],
                "name": "ALDER GUARD STATION",
                "verifiableAvailability": False,
                "dayUse": True,
                "dayUseOnly": True,
                "nonClientFacility": True,
            },
        },
    ],
}

SAMPLE_CAMPSITES_RESPONSE = {
    "totalRecords": 3,
    "totalPages": 1,
    "startIndex": 0,
    "endIndex": 2,
    "control": {"currentPage": 0, "pageSize": 20},
    "records": [
        {
            "id": 500,
            "prodGrpId": 140,
            "prodInfo": {
                "lineOfBusiness": "CAMPING",
                "typeOfUse": "NIGHTLY",
                "typeOfUseLabel": "Overnight",
            },
            "prodGrpName": "Full Hookup",
            "name": "132",
            "details": {
                "siteCode": "132",
                "loopId": 50241,
                "loopName": "Buffalo",
                "ratesStartingFrom": "$41.00",
                "categoriesAttributes": [
                    {
                        "categoryID": 0,
                        "categoryLabel": "Additional Information",
                        "attributes": [
                            {
                                "id": 12,
                                "name": "Maximum Number of People",
                                "value": ["6"],
                                "displayValue": ["6"],
                            },
                            {
                                "id": 18,
                                "name": "Minimum Number of People",
                                "value": ["1"],
                                "displayValue": ["1"],
                            },
                        ],
                    }
                ],
            },
            "reservableType": "WEB_AVAILABLE",
            "available": True,
            "bookingStatus": "AVAILABLE",
            "availabilityGrid": [
                {
                    "date": "2027-06-10",
                    "inventoryCount": 0,
                    "status": "AVAILABLE",
                    "timeblocks": None,
                }
            ],
        },
        {
            "id": 508,
            "prodGrpId": 140,
            "prodInfo": {
                "lineOfBusiness": "CAMPING",
                "typeOfUse": "NIGHTLY",
                "typeOfUseLabel": "Overnight",
            },
            "prodGrpName": "Full Hookup",
            "name": "141",
            "details": {
                "siteCode": "141",
                "loopId": 50241,
                "loopName": "Buffalo",
                "ratesStartingFrom": "$41.00",
            },
            "reservableType": "WEB_AVAILABLE",
            "available": True,
            "bookingStatus": "AVAILABLE",
            "availabilityGrid": [
                {
                    "date": "2027-06-10",
                    "inventoryCount": 0,
                    "status": "AVAILABLE",
                    "timeblocks": None,
                }
            ],
        },
        {
            "id": 59743,
            "prodGrpId": 145,
            "prodInfo": {
                "lineOfBusiness": "CAMPING",
                "typeOfUse": "NIGHTLY",
                "typeOfUseLabel": "Overnight",
            },
            "prodGrpName": "Group Camping",
            "name": "Arapahoe Group Site",
            "details": {
                "siteCode": "Arapahoe Group Site",
                "loopId": 50242,
                "loopName": "Prairie Ridge",
                "ratesStartingFrom": "$216.00",
            },
            "reservableType": "WEB_AVAILABLE",
            "available": True,
            "bookingStatus": "AVAILABLE",
            "availabilityGrid": [
                {
                    "date": "2027-06-10",
                    "inventoryCount": 0,
                    "status": "AVAILABLE",
                    "timeblocks": None,
                }
            ],
        },
    ],
}


def _mock_signin_response() -> requests.Response:
    resp = requests.Response()
    resp.status_code = 200
    resp.cookies.set("idToken", "mock-jwt-token")
    resp.cookies.set("a1Data", "%7B%22sessionID%22%3A%22mock-session%22%7D")
    return resp


def _mock_json_response(payload: dict) -> requests.Response:
    resp = requests.Response()
    resp.status_code = 200
    resp._content = json.dumps(payload).encode("utf-8")
    resp.headers["Content-Type"] = "application/json"
    return resp


def test_colorado_state_parks_authenticate() -> None:
    """
    Verify /signin cookie extraction and header decoding
    """
    prov = ColoradoStateParks()
    with mock.patch.object(
        prov.session, "get", return_value=_mock_signin_response()
    ) as mock_get:
        prov.authenticate()
        mock_get.assert_called_once()
        assert prov.authenticated is True
        assert prov.session.headers["Authorization"] == "mock-jwt-token"
        assert prov.session.headers["A1Data"] == '{"sessionID":"mock-session"}'


def test_colorado_state_parks_find_campgrounds(tmp_path: pathlib.Path) -> None:
    """
    Verify ColoradoStateParks filters to verifiable CO campgrounds and finds Cherry Creek
    """
    prov = ColoradoStateParks()
    prov.__offline_cache_dir__ = tmp_path

    def side_effect(url: str, **kwargs):
        if "signin" in url:
            return _mock_signin_response()
        return _mock_json_response(SAMPLE_SEARCH_RESPONSE)

    with mock.patch.object(prov.session, "get", side_effect=side_effect):
        campgrounds = prov.find_campgrounds(search_string="Cherry Creek", verbose=False)
        assert len(campgrounds) == 1
        assert campgrounds[0].facility_id == 50022
        assert campgrounds[0].facility_name == "Cherry Creek State Park"
        assert campgrounds[0].recreation_area == "Colorado Parks and Wildlife"
        assert 755487 not in prov.reserveamerica_campgrounds


def test_colorado_state_parks_get_campsites(tmp_path: pathlib.Path) -> None:
    """
    Verify parsing Cherry Creek State Park campsites (132, 141, Arapahoe Group Site)
    """
    prov = ColoradoStateParks()
    prov.__offline_cache_dir__ = tmp_path

    def side_effect(url: str, **kwargs):
        if "signin" in url:
            return _mock_signin_response()
        if "/search" in url:
            return _mock_json_response(SAMPLE_SEARCH_RESPONSE)
        return _mock_json_response(SAMPLE_CAMPSITES_RESPONSE)

    with mock.patch.object(prov.session, "get", side_effect=side_effect):
        target_date = datetime.date(2027, 6, 10)
        campsites = prov.get_campsites(
            campground_id=50022,
            start_date=target_date,
            end_date=target_date + datetime.timedelta(days=1),
        )
        assert len(campsites) == 3
        site_names = {c.campsite_site_name for c in campsites}
        assert site_names == {"132", "141", "Arapahoe Group Site"}
        for camp in campsites:
            assert isinstance(camp, AvailableCampsite)
            assert camp.facility_id == 50022
            assert camp.facility_name == "Cherry Creek State Park"


def test_waf_block_raises_reserve_america_error() -> None:
    """
    Verify AWS WAF CAPTCHA response raises ReserveAmericaError
    """
    resp = requests.Response()
    resp.status_code = 405
    resp.headers["x-amzn-waf-action"] = "captcha"
    resp._content = b"<title>Human Verification</title>"
    with pytest.raises(ReserveAmericaError):
        ReserveAmerica._check_waf_block(resp)


def test_search_colorado_state_parks_end_to_end(tmp_path: pathlib.Path) -> None:
    """
    Verify SearchColoradoStateParks returns consolidated AvailableCampsite instances
    """
    window = SearchWindow(
        start_date=datetime.date(2027, 6, 10),
        end_date=datetime.date(2027, 6, 11),
    )

    def side_effect(url: str, **kwargs):
        if "signin" in url:
            return _mock_signin_response()
        if "/search" in url:
            return _mock_json_response(SAMPLE_SEARCH_RESPONSE)
        return _mock_json_response(SAMPLE_CAMPSITES_RESPONSE)

    with mock.patch.object(
        ColoradoStateParks, "__offline_cache_dir__", tmp_path
    ), mock.patch("requests.Session.get", side_effect=side_effect):
        searcher = SearchColoradoStateParks(
            search_window=window,
            campgrounds=[50022],
        )
        results = searcher.get_all_campsites()
        assert len(results) == 3
        assert {r.campsite_site_name for r in results} == {
            "132",
            "141",
            "Arapahoe Group Site",
        }


def test_larimer_county_find_campgrounds_and_equipment_filter(
    tmp_path: pathlib.Path,
) -> None:
    """
    Verify LarimerCounty filters to LARC contract (Horsetooth Reservoir 710105)
    and sends pa99999 and pa109 query parameters for equipment filtering
    """
    prov = LarimerCounty()
    prov.__offline_cache_dir__ = tmp_path
    captured_params = []

    def side_effect(url: str, **kwargs):
        if "signin" in url:
            return _mock_signin_response()
        if "/search" in url:
            return _mock_json_response(SAMPLE_SEARCH_RESPONSE)
        captured_params.append((url, kwargs.get("params", {})))
        return _mock_json_response(SAMPLE_CAMPSITES_RESPONSE)

    with mock.patch.object(prov.session, "get", side_effect=side_effect):
        campgrounds = prov.find_campgrounds(search_string="Horsetooth", verbose=False)
        assert len(campgrounds) == 1
        assert campgrounds[0].facility_id == 710105
        assert campgrounds[0].facility_name == "Horsetooth Reservoir"
        assert campgrounds[0].recreation_area == "Larimer County Agency"
        assert 50022 not in prov.reserveamerica_campgrounds

        target_date = datetime.date(2027, 6, 10)
        campsites = prov.get_campsites(
            campground_id=710105,
            start_date=target_date,
            end_date=target_date + datetime.timedelta(days=1),
            equipment=[("Trailer", 25)],
        )
        assert len(campsites) == 3
        assert len(captured_params) == 1
        req_url, req_params = captured_params[0]
        assert "/products/LARC/710105/campsites" in req_url
        assert req_params["pa99999"] == 2002
        assert req_params["pa109"] == 25
        for camp in campsites:
            assert camp.facility_id == 710105
            assert camp.facility_name == "Horsetooth Reservoir"
            assert camp.booking_url.startswith(
                "https://www.larimercamping.com/camping/horsetooth-reservoir/r/facilityDetails.do"
            )
            assert "arrivalDate=2027-06-10" in camp.booking_url


def test_search_larimer_county_end_to_end(tmp_path: pathlib.Path) -> None:
    """
    Verify SearchLarimerCounty returns consolidated AvailableCampsite instances for Horsetooth Reservoir
    """
    window = SearchWindow(
        start_date=datetime.date(2027, 6, 10),
        end_date=datetime.date(2027, 6, 11),
    )

    def side_effect(url: str, **kwargs):
        if "signin" in url:
            return _mock_signin_response()
        if "/search" in url:
            return _mock_json_response(SAMPLE_SEARCH_RESPONSE)
        return _mock_json_response(SAMPLE_CAMPSITES_RESPONSE)

    with mock.patch.object(
        LarimerCounty, "__offline_cache_dir__", tmp_path
    ), mock.patch("requests.Session.get", side_effect=side_effect):
        searcher = SearchLarimerCounty(
            search_window=window,
            campgrounds=[710105],
            equipment=[("Trailer", 25)],
        )
        results = searcher.get_all_campsites()
        assert len(results) == 3
        assert all(r.facility_id == 710105 for r in results)
