"""
Pydantic models for API responses
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Competitor(BaseModel):
    code: str
    name: str
    noc: str
    competitor_type: Optional[str] = None


class Broadcast(BaseModel):
    drupal_id: str
    title: str
    network: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    day_part: Optional[str] = None
    summary: Optional[str] = None
    video_url: Optional[str] = None
    is_replay: bool = False
    is_medal_session: bool = False


class RundownSegment(BaseModel):
    header: Optional[str] = None
    description: Optional[str] = None
    segment_time: Optional[int] = None


class LinkedEvent(BaseModel):
    event_unit_code: str
    event_unit_name: str
    discipline: str
    medal_flag: bool


class BroadcastDetail(BaseModel):
    drupal_id: str
    title: str
    short_title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    day_part: Optional[str] = None
    summary: Optional[str] = None
    video_url: Optional[str] = None
    peacock_url: Optional[str] = None
    is_medal_session: bool = False
    is_replay: bool = False
    olympic_day: Optional[int] = None
    linked_events: List[LinkedEvent] = []
    rundown: List[RundownSegment] = []


class Event(BaseModel):
    event_unit_code: str
    event_unit_name: str
    discipline: str
    event_name: str
    gender: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    venue: Optional[str] = None
    medal_flag: bool
    phase_name: Optional[str] = None
    status: Optional[str] = None
    competitors: List[Competitor] = []
    broadcasts: List[Broadcast] = []


class ScheduleResponse(BaseModel):
    date: str
    medal_events_count: int
    total_events: int
    events: List[Event]


class TVResponse(BaseModel):
    date: str
    networks: dict


class EuroBroadcast(BaseModel):
    broadcast_id: str
    channel_code: str
    channel_name: str
    country_code: str
    region: str
    title_original: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_live: bool = False
    is_replay: bool = False


class EuroTVResponse(BaseModel):
    date: str
    channels: dict  # channel_code -> list of EuroBroadcast


class DateInfo(BaseModel):
    date: str
    total_events: int
    medal_events: int
    broadcast_count: int


class DatesResponse(BaseModel):
    dates: List[DateInfo]


# Commentary models

class ResultSummary(BaseModel):
    name: str
    noc: str
    position: Optional[int] = None
    mark: Optional[str] = None
    medal_type: Optional[str] = None
    wlt: Optional[str] = None


class CommentaryItem(BaseModel):
    event_unit_code: str
    commentary_type: str  # pre_event or post_event
    discipline: str
    event_name: str
    event_date: Optional[datetime] = None
    medal_flag: bool
    first_paragraph: str
    full_content: str
    status: str
    updated_at: Optional[datetime] = None
    results: List[ResultSummary] = []


class CommentaryResponse(BaseModel):
    previews: List[CommentaryItem] = []
    today_recaps: List[CommentaryItem] = []
    previous_recaps: List[CommentaryItem] = []
