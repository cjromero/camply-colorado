"""
ReserveAmerica API Response Containers
"""

import datetime
from typing import Any, Dict, List, Optional

from camply.containers.base_container import CamplyModel


class ReserveAmericaControl(CamplyModel):
    """
    Pagination Control Metadata
    """

    currentPage: int
    pageSize: int


class ReserveAmericaAgency(CamplyModel):
    """
    Agency Information
    """

    id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    logo: Optional[str] = None
    url: Optional[str] = None


class ReserveAmericaAffiliation(CamplyModel):
    """
    Facility Affiliation
    """

    facilityID: Optional[int] = None
    name: Optional[str] = None
    url: Optional[str] = None
    agencies: Optional[List[ReserveAmericaAgency]] = None


class ReserveAmericaCta(CamplyModel):
    """
    Call to Action Metadata
    """

    caption: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None


class ReserveAmericaCoordinates(CamplyModel):
    """
    Facility Coordinates
    """

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    latitudeDec: Optional[float] = None
    latitudeDegMinSec: Optional[str] = None
    longitudeDec: Optional[float] = None
    longitudeDegMinSec: Optional[str] = None


class ReserveAmericaOfferingSupport(CamplyModel):
    """
    Offering Support Metadata
    """

    business: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None


class ReserveAmericaFacilityDetails(CamplyModel):
    """
    Facility Details inside Search Record
    """

    id: int
    contrCode: str
    stateCodes: Optional[List[str]] = None
    name: str
    baseURL: Optional[str] = None
    imageURL: Optional[str] = None
    crowdriffId: Optional[str] = None
    verifiableAvailability: Optional[bool] = False
    availability: Optional[Any] = None
    affiliation: Optional[ReserveAmericaAffiliation] = None
    facilityTypes: Optional[List[str]] = None
    description: Optional[str] = None
    flexResult: Optional[Any] = None
    cta: Optional[ReserveAmericaCta] = None
    dayUse: Optional[bool] = None
    dayUseOnly: Optional[bool] = None
    ratingSupport: Optional[bool] = None
    rating: Optional[float] = None
    actvAdvInd: Optional[Any] = None
    favoriteSupport: Optional[bool] = None
    favorite: Optional[bool] = None
    webAddress: Optional[str] = None
    coordinates: Optional[ReserveAmericaCoordinates] = None
    hiddenOnMap: Optional[bool] = None
    crossOverCustomLanding: Optional[bool] = None
    legacyRequired: Optional[bool] = None
    lineOfBusinesses: Optional[List[str]] = None
    offeringSupport: Optional[List[ReserveAmericaOfferingSupport]] = None
    nonClientFacility: Optional[bool] = None


class ReserveAmericaRecord(CamplyModel):
    """
    Campground Search Record
    """

    type: Optional[str] = None
    namingId: Optional[str] = None
    namingLabel: Optional[str] = None
    id: int
    name: str
    targetItem: Optional[bool] = None
    matchingFilters: Optional[bool] = None
    reservableType: Optional[str] = None
    available: Optional[bool] = None
    proximity: Optional[float] = None
    summary: Optional[str] = None
    details: ReserveAmericaFacilityDetails
    logoSrc: Optional[str] = None


class ReserveAmericaSearchResponse(CamplyModel):
    """
    Search Endpoint Response
    """

    totalRecords: int
    totalPages: int
    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    control: ReserveAmericaControl
    records: List[ReserveAmericaRecord]
    typesSummary: Optional[Dict[str, int]] = None
    actvAdvInfo: Optional[Any] = None


class ReserveAmericaProdInfo(CamplyModel):
    """
    Product Info on Campsite Record
    """

    lineOfBusiness: Optional[str] = None
    typeOfUse: Optional[str] = None
    typeOfUseLabel: Optional[str] = None


class ReserveAmericaAttributeItem(CamplyModel):
    """
    Individual Campsite Attribute
    """

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[List[str]] = None
    displayValue: Optional[List[str]] = None
    attributeName: Optional[str] = None
    attributeLabel: Optional[str] = None


class ReserveAmericaCategoryAttribute(CamplyModel):
    """
    Category of Campsite Attributes
    """

    categoryID: Optional[int] = None
    categoryLabel: Optional[str] = None
    attributes: Optional[List[ReserveAmericaAttributeItem]] = None


class ReserveAmericaKeySiteAttribute(CamplyModel):
    """
    Key Site Attribute Entry
    """

    key: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None


class ReserveAmericaCampsiteDetails(CamplyModel):
    """
    Detailed Campsite Information
    """

    siteCode: Optional[str] = None
    siteIcon: Optional[str] = None
    stayType: Optional[str] = None
    nonSiteSpecific: Optional[bool] = None
    callCenterReservable: Optional[bool] = None
    mapAreaId: Optional[int] = None
    loopId: Optional[int] = None
    loopName: Optional[str] = None
    siteGroupId: Optional[int] = None
    siteGroupName: Optional[str] = None
    ratesStartingFrom: Optional[str] = None
    categoriesAttributes: Optional[List[ReserveAmericaCategoryAttribute]] = None
    keySiteAttributes: Optional[List[ReserveAmericaKeySiteAttribute]] = None
    imageURL: Optional[str] = None
    siteDescription: Optional[str] = None


class ReserveAmericaAvailabilitySlice(CamplyModel):
    """
    Single Day Availability Entry inside availabilityGrid
    """

    date: datetime.date
    inventoryCount: Optional[int] = 0
    status: str
    timeblocks: Optional[Any] = None


class ReserveAmericaCampsiteRecord(CamplyModel):
    """
    Campsite Record from /products/{contrCode}/{facilityId}/campsites
    """

    id: int
    prodGrpId: Optional[int] = None
    prodInfo: Optional[ReserveAmericaProdInfo] = None
    prodGrpName: Optional[str] = None
    name: str
    details: ReserveAmericaCampsiteDetails
    reservableType: Optional[str] = None
    available: Optional[bool] = False
    bookingStatus: Optional[str] = None
    availableSites: Optional[int] = 0
    availabilityGrid: List[ReserveAmericaAvailabilitySlice] = []
    geolocated: Optional[bool] = None


class ReserveAmericaCampsiteResponse(CamplyModel):
    """
    Campsite Availability Endpoint Response
    """

    totalRecords: int
    totalPages: int
    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    control: ReserveAmericaControl
    records: List[ReserveAmericaCampsiteRecord] = []
