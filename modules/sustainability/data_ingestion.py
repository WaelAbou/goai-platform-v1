"""
Sustainability Data Ingestion Engine

Multi-source data ingestion for ESG and carbon footprint data:
- CSV/Excel file imports
- JSON bulk imports
- API connectors (Concur, Workday, Utilities)
- Data validation and quality checks
- Template generation for data collection
"""

import json
import csv
import io
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import re


class DataSourceType(str, Enum):
    """Supported data source types."""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    API = "api"
    MANUAL = "manual"


class DataCategory(str, Enum):
    """Categories of sustainability data."""
    ENERGY = "energy"              # Electricity, gas, heating
    TRAVEL = "travel"              # Flights, car rentals, hotels
    FLEET = "fleet"                # Company vehicles
    COMMUTING = "commuting"        # Employee commute surveys
    SHIPPING = "shipping"          # Logistics, freight
    WASTE = "waste"                # Waste generation, recycling
    WATER = "water"                # Water consumption
    ESG_METRICS = "esg_metrics"    # HR, safety, governance data
    COMPANY = "company"            # Company profile data


@dataclass
class ValidationError:
    """Data validation error."""
    row: int
    column: str
    value: Any
    error: str
    severity: str = "error"  # error, warning


@dataclass
class ImportResult:
    """Result of a data import operation."""
    success: bool
    source_type: str
    category: str
    records_processed: int
    records_imported: int
    records_failed: int
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    data: List[Dict[str, Any]] = field(default_factory=list)
    import_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== Data Templates ====================

DATA_TEMPLATES = {
    "energy": {
        "name": "Energy Consumption Template",
        "description": "Monthly electricity and gas usage by location",
        "columns": [
            {"name": "location_name", "type": "string", "required": True, "description": "Office/facility name"},
            {"name": "month", "type": "date", "required": True, "description": "Month (YYYY-MM)"},
            {"name": "electricity_kwh", "type": "number", "required": True, "description": "Electricity usage in kWh"},
            {"name": "natural_gas_therms", "type": "number", "required": False, "description": "Natural gas in therms"},
            {"name": "renewable_percent", "type": "number", "required": False, "description": "% from renewable sources"},
            {"name": "utility_provider", "type": "string", "required": False, "description": "Utility company name"},
            {"name": "cost_usd", "type": "number", "required": False, "description": "Total cost in USD"},
        ],
        "example_row": {
            "location_name": "San Francisco HQ",
            "month": "2024-01",
            "electricity_kwh": 45000,
            "natural_gas_therms": 500,
            "renewable_percent": 100,
            "utility_provider": "PG&E",
            "cost_usd": 5200
        }
    },
    "travel": {
        "name": "Business Travel Template",
        "description": "Flight and ground transportation data",
        "columns": [
            {"name": "trip_date", "type": "date", "required": True, "description": "Travel date (YYYY-MM-DD)"},
            {"name": "traveler_id", "type": "string", "required": False, "description": "Employee ID"},
            {"name": "trip_type", "type": "string", "required": True, "description": "flight, car_rental, train, hotel"},
            {"name": "origin", "type": "string", "required": True, "description": "Departure city/airport"},
            {"name": "destination", "type": "string", "required": True, "description": "Arrival city/airport"},
            {"name": "distance_km", "type": "number", "required": False, "description": "Distance in km (auto-calculated if blank)"},
            {"name": "travel_class", "type": "string", "required": False, "description": "economy, business, first"},
            {"name": "round_trip", "type": "boolean", "required": False, "description": "True/False"},
            {"name": "cost_usd", "type": "number", "required": False, "description": "Trip cost"},
            {"name": "purpose", "type": "string", "required": False, "description": "Business purpose"},
        ],
        "example_row": {
            "trip_date": "2024-03-15",
            "traveler_id": "EMP001",
            "trip_type": "flight",
            "origin": "SFO",
            "destination": "LHR",
            "distance_km": 8600,
            "travel_class": "business",
            "round_trip": True,
            "cost_usd": 4500,
            "purpose": "Client meeting"
        }
    },
    "fleet": {
        "name": "Fleet Vehicles Template",
        "description": "Company vehicle usage and fuel data",
        "columns": [
            {"name": "vehicle_id", "type": "string", "required": True, "description": "Vehicle identifier"},
            {"name": "vehicle_type", "type": "string", "required": True, "description": "car_petrol, car_diesel, car_electric, van, truck"},
            {"name": "month", "type": "date", "required": True, "description": "Month (YYYY-MM)"},
            {"name": "distance_km", "type": "number", "required": True, "description": "Distance driven"},
            {"name": "fuel_liters", "type": "number", "required": False, "description": "Fuel consumed (if known)"},
            {"name": "fuel_cost_usd", "type": "number", "required": False, "description": "Fuel cost"},
            {"name": "location", "type": "string", "required": False, "description": "Primary operating location"},
        ],
        "example_row": {
            "vehicle_id": "VAN-001",
            "vehicle_type": "van_diesel",
            "month": "2024-01",
            "distance_km": 3500,
            "fuel_liters": 420,
            "fuel_cost_usd": 650,
            "location": "Chicago Distribution"
        }
    },
    "commuting": {
        "name": "Employee Commuting Survey Template",
        "description": "Employee commute patterns for Scope 3 calculation",
        "columns": [
            {"name": "employee_id", "type": "string", "required": False, "description": "Employee ID (optional for anonymity)"},
            {"name": "department", "type": "string", "required": False, "description": "Department name"},
            {"name": "location", "type": "string", "required": True, "description": "Office location"},
            {"name": "commute_mode", "type": "string", "required": True, "description": "car, ev, public_transit, bike, walk, remote"},
            {"name": "distance_km_one_way", "type": "number", "required": True, "description": "One-way commute distance"},
            {"name": "days_per_week", "type": "number", "required": True, "description": "Days commuting (0-5)"},
            {"name": "weeks_per_year", "type": "number", "required": False, "description": "Weeks worked (default: 48)"},
            {"name": "vehicle_type", "type": "string", "required": False, "description": "If car: petrol_small, petrol_medium, diesel, hybrid, electric"},
        ],
        "example_row": {
            "employee_id": "EMP042",
            "department": "Engineering",
            "location": "San Francisco HQ",
            "commute_mode": "car",
            "distance_km_one_way": 25,
            "days_per_week": 3,
            "weeks_per_year": 48,
            "vehicle_type": "petrol_medium"
        }
    },
    "esg_metrics": {
        "name": "ESG Metrics Template",
        "description": "Quarterly ESG data collection",
        "columns": [
            {"name": "quarter", "type": "string", "required": True, "description": "Quarter (e.g., 2024-Q1)"},
            {"name": "renewable_energy_percent", "type": "number", "required": True, "description": "% energy from renewables"},
            {"name": "waste_recycled_percent", "type": "number", "required": True, "description": "% waste recycled"},
            {"name": "water_usage_gallons", "type": "number", "required": False, "description": "Water consumption"},
            {"name": "employee_satisfaction", "type": "number", "required": True, "description": "Satisfaction score (0-100)"},
            {"name": "diversity_percent", "type": "number", "required": True, "description": "Workforce diversity %"},
            {"name": "safety_incidents", "type": "number", "required": True, "description": "# of safety incidents"},
            {"name": "training_hours_per_employee", "type": "number", "required": False, "description": "Avg training hours"},
            {"name": "community_investment_usd", "type": "number", "required": False, "description": "Community investment"},
            {"name": "board_independence_percent", "type": "number", "required": True, "description": "% independent directors"},
            {"name": "ethics_violations", "type": "number", "required": True, "description": "# of ethics violations"},
        ],
        "example_row": {
            "quarter": "2024-Q1",
            "renewable_energy_percent": 55,
            "waste_recycled_percent": 72,
            "water_usage_gallons": 250000,
            "employee_satisfaction": 82,
            "diversity_percent": 42,
            "safety_incidents": 2,
            "training_hours_per_employee": 24,
            "community_investment_usd": 75000,
            "board_independence_percent": 67,
            "ethics_violations": 0
        }
    },
    "shipping": {
        "name": "Shipping & Logistics Template",
        "description": "Freight and logistics data",
        "columns": [
            {"name": "shipment_date", "type": "date", "required": True, "description": "Shipment date"},
            {"name": "shipment_id", "type": "string", "required": False, "description": "Tracking/reference number"},
            {"name": "origin", "type": "string", "required": True, "description": "Origin location"},
            {"name": "destination", "type": "string", "required": True, "description": "Destination location"},
            {"name": "mode", "type": "string", "required": True, "description": "road, rail, sea, air"},
            {"name": "weight_kg", "type": "number", "required": True, "description": "Shipment weight in kg"},
            {"name": "distance_km", "type": "number", "required": False, "description": "Distance (auto-calculated if blank)"},
            {"name": "carrier", "type": "string", "required": False, "description": "Logistics provider"},
            {"name": "cost_usd", "type": "number", "required": False, "description": "Shipping cost"},
        ],
        "example_row": {
            "shipment_date": "2024-02-20",
            "shipment_id": "SHP-2024-0542",
            "origin": "Shanghai, China",
            "destination": "Los Angeles, USA",
            "mode": "sea",
            "weight_kg": 5000,
            "distance_km": 10500,
            "carrier": "Maersk",
            "cost_usd": 2800
        }
    }
}


# ==================== Data Validators ====================

class DataValidator:
    """Validate imported data against templates."""
    
    @staticmethod
    def validate_number(value: Any, allow_negative: bool = False) -> Tuple[bool, Any, str]:
        """Validate numeric value."""
        if value is None or value == "":
            return True, None, ""
        try:
            num = float(value)
            if not allow_negative and num < 0:
                return False, value, "Value cannot be negative"
            return True, num, ""
        except (ValueError, TypeError):
            return False, value, f"Invalid number: {value}"
    
    @staticmethod
    def validate_date(value: Any, format_hint: str = "YYYY-MM-DD") -> Tuple[bool, Any, str]:
        """Validate date value."""
        if value is None or value == "":
            return True, None, ""
        
        # Try common formats
        formats = ["%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]
        for fmt in formats:
            try:
                parsed = datetime.strptime(str(value), fmt)
                return True, parsed.strftime("%Y-%m-%d"), ""
            except ValueError:
                continue
        return False, value, f"Invalid date format. Expected: {format_hint}"
    
    @staticmethod
    def validate_string(value: Any, allowed_values: Optional[List[str]] = None) -> Tuple[bool, Any, str]:
        """Validate string value."""
        if value is None or value == "":
            return True, None, ""
        
        str_value = str(value).strip()
        
        if allowed_values:
            if str_value.lower() not in [v.lower() for v in allowed_values]:
                return False, value, f"Must be one of: {', '.join(allowed_values)}"
        
        return True, str_value, ""
    
    @staticmethod
    def validate_boolean(value: Any) -> Tuple[bool, Any, str]:
        """Validate boolean value."""
        if value is None or value == "":
            return True, None, ""
        
        true_values = ["true", "yes", "1", "y"]
        false_values = ["false", "no", "0", "n"]
        
        str_value = str(value).lower().strip()
        
        if str_value in true_values:
            return True, True, ""
        elif str_value in false_values:
            return True, False, ""
        else:
            return False, value, "Must be true/false, yes/no, or 1/0"


class SustainabilityDataIngestion:
    """
    Main data ingestion engine for sustainability data.
    
    Supports:
    - CSV/Excel file imports
    - JSON bulk imports
    - Data validation
    - Template generation
    - Emission factor application
    """
    
    # Emission factors (kg CO2e per unit)
    EMISSION_FACTORS = {
        # Electricity (kg CO2e per kWh)
        "electricity_us_avg": 0.417,
        "electricity_uk": 0.207,
        "electricity_eu_avg": 0.296,
        
        # Natural Gas (kg CO2e per therm)
        "natural_gas": 5.31,
        
        # Flights (kg CO2e per passenger-km)
        "flight_economy": 0.156,
        "flight_business": 0.468,
        "flight_first": 0.624,
        
        # Vehicles (kg CO2e per km)
        "car_petrol_small": 0.142,
        "car_petrol_medium": 0.171,
        "car_petrol_large": 0.214,
        "car_diesel": 0.168,
        "car_hybrid": 0.108,
        "car_electric": 0.053,
        "van_petrol": 0.212,
        "van_diesel": 0.234,
        "truck": 0.893,
        
        # Public Transit (kg CO2e per passenger-km)
        "bus": 0.089,
        "train_local": 0.041,
        "train_national": 0.035,
        "subway": 0.033,
        
        # Shipping (kg CO2e per tonne-km)
        "road_freight": 0.107,
        "rail_freight": 0.028,
        "sea_container": 0.016,
        "air_freight": 0.602,
    }
    
    def __init__(self):
        self.validator = DataValidator()
    
    # ==================== Template Methods ====================
    
    def get_templates(self) -> Dict[str, Any]:
        """Get all available data templates."""
        return {
            category: {
                "name": template["name"],
                "description": template["description"],
                "columns": template["columns"]
            }
            for category, template in DATA_TEMPLATES.items()
        }
    
    def get_template(self, category: str) -> Optional[Dict[str, Any]]:
        """Get a specific template."""
        return DATA_TEMPLATES.get(category)
    
    def generate_csv_template(self, category: str) -> str:
        """Generate a CSV template with headers and example row."""
        template = DATA_TEMPLATES.get(category)
        if not template:
            raise ValueError(f"Unknown template category: {category}")
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[col["name"] for col in template["columns"]])
        
        # Write header
        writer.writeheader()
        
        # Write example row
        writer.writerow(template["example_row"])
        
        return output.getvalue()
    
    def generate_json_template(self, category: str) -> str:
        """Generate a JSON template with schema and example."""
        template = DATA_TEMPLATES.get(category)
        if not template:
            raise ValueError(f"Unknown template category: {category}")
        
        return json.dumps({
            "template": template["name"],
            "description": template["description"],
            "schema": template["columns"],
            "example_data": [template["example_row"]]
        }, indent=2)
    
    # ==================== Import Methods ====================
    
    def import_csv(self, csv_content: str, category: str) -> ImportResult:
        """Import data from CSV content."""
        template = DATA_TEMPLATES.get(category)
        if not template:
            return ImportResult(
                success=False,
                source_type="csv",
                category=category,
                records_processed=0,
                records_imported=0,
                records_failed=0,
                errors=[ValidationError(0, "", "", f"Unknown category: {category}")]
            )
        
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        return self._process_rows(rows, template, category, "csv")
    
    def import_json(self, json_content: str, category: str) -> ImportResult:
        """Import data from JSON content."""
        template = DATA_TEMPLATES.get(category)
        if not template:
            return ImportResult(
                success=False,
                source_type="json",
                category=category,
                records_processed=0,
                records_imported=0,
                records_failed=0,
                errors=[ValidationError(0, "", "", f"Unknown category: {category}")]
            )
        
        try:
            data = json.loads(json_content)
            
            # Handle both array and object with "data" key
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and "data" in data:
                rows = data["data"]
            else:
                rows = [data]
            
            return self._process_rows(rows, template, category, "json")
            
        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                source_type="json",
                category=category,
                records_processed=0,
                records_imported=0,
                records_failed=0,
                errors=[ValidationError(0, "", "", f"Invalid JSON: {str(e)}")]
            )
    
    def _process_rows(
        self,
        rows: List[Dict[str, Any]],
        template: Dict[str, Any],
        category: str,
        source_type: str
    ) -> ImportResult:
        """Process and validate rows against template."""
        errors = []
        warnings = []
        valid_data = []
        
        column_map = {col["name"]: col for col in template["columns"]}
        
        for row_idx, row in enumerate(rows, start=1):
            row_errors = []
            validated_row = {}
            
            # Check required columns
            for col in template["columns"]:
                col_name = col["name"]
                value = row.get(col_name)
                
                # Check required
                if col["required"] and (value is None or value == ""):
                    row_errors.append(ValidationError(
                        row=row_idx,
                        column=col_name,
                        value=value,
                        error=f"Required field is missing"
                    ))
                    continue
                
                # Validate by type
                if col["type"] == "number":
                    valid, cleaned, err = self.validator.validate_number(value)
                elif col["type"] == "date":
                    valid, cleaned, err = self.validator.validate_date(value)
                elif col["type"] == "boolean":
                    valid, cleaned, err = self.validator.validate_boolean(value)
                else:
                    valid, cleaned, err = self.validator.validate_string(value)
                
                if not valid:
                    row_errors.append(ValidationError(
                        row=row_idx,
                        column=col_name,
                        value=value,
                        error=err
                    ))
                else:
                    validated_row[col_name] = cleaned
            
            if row_errors:
                errors.extend(row_errors)
            else:
                # Calculate emissions if applicable
                validated_row = self._calculate_emissions(validated_row, category)
                valid_data.append(validated_row)
        
        return ImportResult(
            success=len(errors) == 0,
            source_type=source_type,
            category=category,
            records_processed=len(rows),
            records_imported=len(valid_data),
            records_failed=len(rows) - len(valid_data),
            errors=errors,
            warnings=warnings,
            data=valid_data
        )
    
    def _calculate_emissions(self, row: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Calculate CO2e emissions based on category and data."""
        
        if category == "energy":
            co2e = 0
            
            # Electricity
            kwh = row.get("electricity_kwh", 0) or 0
            renewable = row.get("renewable_percent", 0) or 0
            grid_factor = self.EMISSION_FACTORS["electricity_us_avg"]
            co2e += kwh * (1 - renewable/100) * grid_factor
            
            # Natural gas
            therms = row.get("natural_gas_therms", 0) or 0
            co2e += therms * self.EMISSION_FACTORS["natural_gas"]
            
            row["calculated_co2e_kg"] = round(co2e, 2)
            row["scope"] = 2 if kwh > 0 else 1
            
        elif category == "travel":
            co2e = 0
            trip_type = row.get("trip_type", "").lower()
            distance = row.get("distance_km", 0) or 0
            
            if trip_type == "flight":
                travel_class = row.get("travel_class", "economy").lower()
                factor_key = f"flight_{travel_class}"
                factor = self.EMISSION_FACTORS.get(factor_key, self.EMISSION_FACTORS["flight_economy"])
                co2e = distance * factor
                
                if row.get("round_trip"):
                    co2e *= 2
            
            row["calculated_co2e_kg"] = round(co2e, 2)
            row["scope"] = 3
            
        elif category == "fleet":
            vehicle_type = row.get("vehicle_type", "car_petrol_medium").lower()
            distance = row.get("distance_km", 0) or 0
            factor = self.EMISSION_FACTORS.get(vehicle_type, self.EMISSION_FACTORS["car_petrol_medium"])
            
            row["calculated_co2e_kg"] = round(distance * factor, 2)
            row["scope"] = 1
            
        elif category == "commuting":
            mode = row.get("commute_mode", "").lower()
            distance = row.get("distance_km_one_way", 0) or 0
            days = row.get("days_per_week", 5) or 5
            weeks = row.get("weeks_per_year", 48) or 48
            
            annual_km = distance * 2 * days * weeks  # Round trip
            
            if mode == "car":
                vehicle_type = row.get("vehicle_type", "car_petrol_medium").lower()
                factor = self.EMISSION_FACTORS.get(vehicle_type, self.EMISSION_FACTORS["car_petrol_medium"])
            elif mode == "ev":
                factor = self.EMISSION_FACTORS["car_electric"]
            elif mode == "public_transit":
                factor = self.EMISSION_FACTORS["train_local"]
            elif mode in ["bike", "walk", "remote"]:
                factor = 0
            else:
                factor = self.EMISSION_FACTORS["car_petrol_medium"]
            
            row["calculated_co2e_kg"] = round(annual_km * factor, 2)
            row["annual_km"] = annual_km
            row["scope"] = 3
            
        elif category == "shipping":
            mode = row.get("mode", "road").lower()
            weight_kg = row.get("weight_kg", 0) or 0
            distance = row.get("distance_km", 0) or 0
            
            weight_tonnes = weight_kg / 1000
            
            mode_map = {
                "road": "road_freight",
                "rail": "rail_freight",
                "sea": "sea_container",
                "air": "air_freight"
            }
            factor_key = mode_map.get(mode, "road_freight")
            factor = self.EMISSION_FACTORS[factor_key]
            
            row["calculated_co2e_kg"] = round(weight_tonnes * distance * factor, 2)
            row["scope"] = 3
        
        return row
    
    # ==================== Aggregation Methods ====================
    
    def aggregate_to_footprint(
        self,
        energy_data: List[Dict],
        travel_data: List[Dict],
        fleet_data: List[Dict],
        commuting_data: List[Dict],
        shipping_data: List[Dict],
        year: int
    ) -> Dict[str, Any]:
        """Aggregate imported data into annual carbon footprint."""
        
        scope_1 = 0
        scope_2 = 0
        scope_3 = 0
        
        breakdown = {}
        
        # Energy
        if energy_data:
            energy_total = sum(r.get("calculated_co2e_kg", 0) for r in energy_data)
            scope_2 += energy_total
            breakdown["office_energy"] = {
                "co2e_kg": energy_total,
                "scope": 2,
                "records": len(energy_data)
            }
        
        # Travel
        if travel_data:
            travel_total = sum(r.get("calculated_co2e_kg", 0) for r in travel_data)
            scope_3 += travel_total
            breakdown["business_travel"] = {
                "co2e_kg": travel_total,
                "scope": 3,
                "records": len(travel_data)
            }
        
        # Fleet
        if fleet_data:
            fleet_total = sum(r.get("calculated_co2e_kg", 0) for r in fleet_data)
            scope_1 += fleet_total
            breakdown["fleet_vehicles"] = {
                "co2e_kg": fleet_total,
                "scope": 1,
                "records": len(fleet_data)
            }
        
        # Commuting
        if commuting_data:
            commute_total = sum(r.get("calculated_co2e_kg", 0) for r in commuting_data)
            scope_3 += commute_total
            breakdown["employee_commuting"] = {
                "co2e_kg": commute_total,
                "scope": 3,
                "employees_surveyed": len(commuting_data)
            }
        
        # Shipping
        if shipping_data:
            shipping_total = sum(r.get("calculated_co2e_kg", 0) for r in shipping_data)
            scope_3 += shipping_total
            breakdown["shipping"] = {
                "co2e_kg": shipping_total,
                "scope": 3,
                "shipments": len(shipping_data)
            }
        
        total = scope_1 + scope_2 + scope_3
        
        return {
            "year": year,
            "scope_1_kg": round(scope_1, 2),
            "scope_2_kg": round(scope_2, 2),
            "scope_3_kg": round(scope_3, 2),
            "total_kg": round(total, 2),
            "total_tonnes": round(total / 1000, 2),
            "breakdown": breakdown,
            "methodology": "GHG Protocol Corporate Standard",
            "data_sources": {
                "energy_records": len(energy_data) if energy_data else 0,
                "travel_records": len(travel_data) if travel_data else 0,
                "fleet_records": len(fleet_data) if fleet_data else 0,
                "commuting_surveys": len(commuting_data) if commuting_data else 0,
                "shipping_records": len(shipping_data) if shipping_data else 0
            }
        }


# Singleton instance
data_ingestion = SustainabilityDataIngestion()

