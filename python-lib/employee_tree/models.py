from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class EmployeeRecord:
    employee_id: str
    manager_id: Optional[str]
    full_name: str
    job_title: str
    department: str
    location: str
    level: str
    employment_status: str
    email: Optional[str]
    team_name: Optional[str]
    photo_url: Optional[str]
    start_date: Optional[str]
    max_direct_reports: Optional[int]
    can_be_manager: bool
    sort_order: Optional[int]
    row_number: int


@dataclass(frozen=True)
class ManagerConstraint:
    manager_id: str
    max_direct_reports: Optional[int]
    allowed_departments: Sequence[str]
    allowed_locations: Sequence[str]
    min_child_level: Optional[str]
    max_child_level: Optional[str]
    rule_note: Optional[str]
    row_number: int
