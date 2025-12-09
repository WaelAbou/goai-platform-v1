"""
Smart Document Ingestion for Sustainability Data

Uses OCR + LLM to automatically:
1. Detect document type (utility bill, travel receipt, invoice, etc.)
2. Extract relevant sustainability data
3. Route to appropriate template
4. Calculate emissions

Supported document types:
- Utility bills (electricity, gas, water)
- Travel receipts (flights, car rentals)
- Fuel receipts (fleet vehicles)
- Shipping invoices (logistics)
- ESG reports (quarterly metrics)
"""

import json
import base64
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re


class SustainabilityDocumentType(str, Enum):
    """Sustainability-relevant document types."""
    UTILITY_BILL_ELECTRIC = "utility_bill_electric"
    UTILITY_BILL_GAS = "utility_bill_gas"
    UTILITY_BILL_WATER = "utility_bill_water"
    FLIGHT_RECEIPT = "flight_receipt"
    CAR_RENTAL_RECEIPT = "car_rental_receipt"
    HOTEL_RECEIPT = "hotel_receipt"
    FUEL_RECEIPT = "fuel_receipt"
    SHIPPING_INVOICE = "shipping_invoice"
    ESG_REPORT = "esg_report"
    EXPENSE_REPORT = "expense_report"
    UNKNOWN = "unknown"


@dataclass
class DocumentClassification:
    """Result of document classification."""
    document_type: SustainabilityDocumentType
    confidence: float
    reasoning: str
    suggested_template: str
    extracted_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedData:
    """Extracted sustainability data from document."""
    document_type: SustainabilityDocumentType
    template: str
    data: Dict[str, Any]
    raw_text: str
    confidence: float
    extraction_notes: List[str] = field(default_factory=list)
    calculated_co2e_kg: Optional[float] = None


# Document classification prompt
CLASSIFICATION_PROMPT = """Analyze this document text and classify it for sustainability/ESG data extraction.

DOCUMENT TEXT:
{text}

Classify this document into ONE of these categories:
1. utility_bill_electric - ONLY for electricity bills with kWh usage from utility providers (e.g., PG&E, ConEd)
2. utility_bill_gas - ONLY for natural gas bills with therms/CCF usage
3. utility_bill_water - ONLY for water bills with gallon/cubic meter usage
4. flight_receipt - ONLY for airline tickets, boarding passes, or flight booking confirmations with flight numbers
5. car_rental_receipt - ONLY for car rental agreements with pickup/return dates
6. hotel_receipt - ONLY for hotel invoices with room charges
7. fuel_receipt - ONLY for gas station receipts with fuel quantity in gallons/liters
8. shipping_invoice - ONLY for freight/shipping invoices with weight and tracking numbers
9. esg_report - ONLY for formal quarterly/annual ESG or sustainability reports with multiple metrics across E/S/G categories
10. expense_report - ONLY for travel expense reimbursement forms with multiple line items
11. unknown - Use this for ANY document that doesn't CLEARLY fit categories 1-10

IMPORTANT: Only use categories 1-10 if you are VERY confident (>85%) the document matches that specific type.
If the document is related to sustainability but doesn't fit a specific category (e.g., water footprint assessment, 
carbon offset certificate, EV charging report, waste diversion report), classify as "unknown" so a custom template can be created.

Respond in JSON format:
{{
    "document_type": "<type from list above>",
    "confidence": <0.0-1.0>,
    "reasoning": "<why you classified it this way>",
    "key_indicators": ["<list of keywords/values that helped classify>"]
}}
"""

# Extraction prompts for each document type
EXTRACTION_PROMPTS = {
    SustainabilityDocumentType.UTILITY_BILL_ELECTRIC: """Extract electricity bill data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- account_holder: Customer/account name
- location_name: Service address or location
- billing_period_start: Start date (YYYY-MM-DD)
- billing_period_end: End date (YYYY-MM-DD)
- electricity_kwh: Total kWh consumed (number only)
- cost_usd: Total amount due (number only)
- utility_provider: Name of utility company
- renewable_percent: Percentage from renewable sources if mentioned (number only)

Respond in JSON format matching the fields above.""",

    SustainabilityDocumentType.UTILITY_BILL_GAS: """Extract natural gas bill data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- account_holder: Customer/account name
- location_name: Service address or location
- billing_period_start: Start date (YYYY-MM-DD)
- billing_period_end: End date (YYYY-MM-DD)
- natural_gas_therms: Total therms consumed (number only)
- natural_gas_ccf: Total CCF if therms not available (number only)
- cost_usd: Total amount due (number only)
- utility_provider: Name of utility company

Respond in JSON format matching the fields above.""",

    SustainabilityDocumentType.FLIGHT_RECEIPT: """Extract flight travel data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- traveler_name: Passenger name
- trip_date: Date of travel (YYYY-MM-DD)
- origin: Departure airport code or city
- destination: Arrival airport code or city
- travel_class: economy, business, or first
- airline: Airline name
- flight_number: Flight number if available
- round_trip: true/false if this is round trip
- cost_usd: Ticket price (number only)

If multiple flights/legs, return an array of objects.

Respond in JSON format.""",

    SustainabilityDocumentType.CAR_RENTAL_RECEIPT: """Extract car rental data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- renter_name: Customer name
- rental_start_date: Start date (YYYY-MM-DD)
- rental_end_date: End date (YYYY-MM-DD)
- pickup_location: Pickup location
- dropoff_location: Return location
- vehicle_type: Type of vehicle (compact, midsize, SUV, etc.)
- distance_km: Total distance driven if available (number only)
- fuel_type: petrol, diesel, electric, hybrid
- rental_company: Rental company name
- cost_usd: Total cost (number only)

Respond in JSON format.""",

    SustainabilityDocumentType.FUEL_RECEIPT: """Extract fuel purchase data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- purchase_date: Date (YYYY-MM-DD)
- fuel_type: petrol, diesel
- fuel_liters: Liters purchased (number only)
- fuel_gallons: Gallons if liters not available (number only)
- cost_usd: Total cost (number only)
- station_name: Gas station name
- vehicle_id: License plate or vehicle ID if shown
- odometer: Odometer reading if shown (number only)

Respond in JSON format.""",

    SustainabilityDocumentType.SHIPPING_INVOICE: """Extract shipping/freight data from this text.

DOCUMENT TEXT:
{text}

Extract these fields (use null if not found):
- shipment_date: Shipment date (YYYY-MM-DD)
- shipment_id: Tracking or reference number
- origin: Origin city/location
- destination: Destination city/location
- weight_kg: Weight in kg (number only)
- weight_lbs: Weight in lbs if kg not available (number only)
- shipping_mode: road, rail, sea, air
- carrier: Shipping company name
- cost_usd: Shipping cost (number only)

If multiple shipments, return an array.

Respond in JSON format.""",

    SustainabilityDocumentType.EXPENSE_REPORT: """Extract travel/expense items from this report.

DOCUMENT TEXT:
{text}

Extract each expense item with:
- date: Date (YYYY-MM-DD)
- category: flight, car_rental, hotel, fuel, meal, other
- description: Brief description
- amount_usd: Amount (number only)
- origin: If travel, origin location
- destination: If travel, destination

Return an array of expense objects.

Respond in JSON format.""",

    SustainabilityDocumentType.ESG_REPORT: """Extract sustainability metrics from this ESG report.

DOCUMENT TEXT:
{text}

Extract these metrics where available:
- report_period: Time period covered
- total_energy_kwh: Total electricity consumption (number)
- renewable_energy_percent: Percentage from renewable sources (number)
- natural_gas_therms: Natural gas usage (number)
- business_travel_flights: Number of flights
- business_travel_km: Total flight distance (number)
- fleet_fuel_gallons: Fleet fuel consumption (number)
- fleet_fuel_liters: Fleet fuel in liters if available (number)
- shipping_weight_tonnes: Total shipping weight (number)
- shipping_distance_km: Total shipping distance (number)
- emissions_scope_1_kg: Scope 1 emissions if reported (number)
- emissions_scope_2_kg: Scope 2 emissions if reported (number)
- emissions_scope_3_kg: Scope 3 emissions if reported (number)

Respond in JSON format.""",
}


class SmartDocumentProcessor:
    
    # Common airport distances (km) for better CO2e calculations
    AIRPORT_DISTANCES = {
        # Format: (origin, dest): distance_km (one-way)
        ("SFO", "JFK"): 4140,
        ("JFK", "SFO"): 4140,
        ("SFO", "LAX"): 540,
        ("LAX", "SFO"): 540,
        ("SFO", "SEA"): 1090,
        ("SEA", "SFO"): 1090,
        ("SFO", "LHR"): 8620,
        ("LHR", "SFO"): 8620,
        ("JFK", "LHR"): 5540,
        ("LHR", "JFK"): 5540,
        ("LAX", "JFK"): 3980,
        ("JFK", "LAX"): 3980,
        ("ORD", "JFK"): 1190,
        ("JFK", "ORD"): 1190,
        ("DFW", "SFO"): 2350,
        ("SFO", "DFW"): 2350,
        ("LAX", "LHR"): 8760,
        ("LHR", "LAX"): 8760,
        ("SFO", "NRT"): 8280,  # Tokyo
        ("NRT", "SFO"): 8280,
        ("JFK", "CDG"): 5840,  # Paris
        ("CDG", "JFK"): 5840,
    }
    """
    Intelligent document processor for sustainability data.
    
    Uses OCR for text extraction and LLM for:
    - Document type classification
    - Structured data extraction
    - Emission calculation
    """
    
    # Template mapping
    TEMPLATE_MAP = {
        SustainabilityDocumentType.UTILITY_BILL_ELECTRIC: "energy",
        SustainabilityDocumentType.UTILITY_BILL_GAS: "energy",
        SustainabilityDocumentType.UTILITY_BILL_WATER: "energy",
        SustainabilityDocumentType.FLIGHT_RECEIPT: "travel",
        SustainabilityDocumentType.CAR_RENTAL_RECEIPT: "travel",
        SustainabilityDocumentType.HOTEL_RECEIPT: "travel",
        SustainabilityDocumentType.FUEL_RECEIPT: "fleet",
        SustainabilityDocumentType.SHIPPING_INVOICE: "shipping",
        SustainabilityDocumentType.EXPENSE_REPORT: "travel",
        SustainabilityDocumentType.ESG_REPORT: "esg_summary",
    }
    
    # Emission factors (EPA + DEFRA 2023)
    EMISSION_FACTORS = {
        # Electricity
        "electricity_us_avg": 0.417,  # kg CO2e per kWh
        "electricity_uk": 0.207,      # kg CO2e per kWh
        "electricity_eu": 0.276,      # kg CO2e per kWh
        
        # Natural Gas
        "natural_gas_therm": 5.31,    # kg CO2e per therm
        "natural_gas_ccf": 5.31,      # Approximate (1 CCF ≈ 1 therm)
        "natural_gas_m3": 2.02,       # kg CO2e per cubic meter
        
        # Flights (per passenger-km)
        "flight_economy_km": 0.156,
        "flight_business_km": 0.468,
        "flight_first_km": 0.624,
        "flight_domestic_km": 0.246,  # Short-haul domestic
        
        # Vehicles
        "car_petrol_km": 0.171,       # kg CO2e per km
        "car_diesel_km": 0.168,
        "car_electric_km": 0.053,
        "car_hybrid_km": 0.103,
        
        # Fuel (per liter)
        "fuel_petrol_liter": 2.31,
        "fuel_diesel_liter": 2.68,
        "fuel_lpg_liter": 1.51,
        
        # Shipping (per tonne-km)
        "shipping_road_tkm": 0.107,
        "shipping_rail_tkm": 0.028,
        "shipping_sea_tkm": 0.016,
        "shipping_air_tkm": 0.602,
    }
    
    def __init__(self):
        self.ocr_engine = None
        self.llm_router = None
        
    def set_ocr_engine(self, ocr_engine):
        """Set OCR engine for text extraction."""
        self.ocr_engine = ocr_engine
        
    def set_llm_router(self, llm_router):
        """Set LLM router for classification and extraction."""
        self.llm_router = llm_router
    
    async def process_document(
        self,
        image_base64: Optional[str] = None,
        text_content: Optional[str] = None,
        force_type: Optional[SustainabilityDocumentType] = None
    ) -> ExtractedData:
        """
        Process a document and extract sustainability data.
        
        Args:
            image_base64: Base64-encoded image (uses OCR)
            text_content: Plain text content (skips OCR)
            force_type: Override auto-classification
            
        Returns:
            ExtractedData with structured sustainability data
        """
        # Step 1: Get text content
        if text_content:
            raw_text = text_content
        elif image_base64 and self.ocr_engine:
            # Decode base64 to bytes
            import base64
            image_bytes = base64.b64decode(image_base64)
            
            # Extract text using OCR
            ocr_result = await self.ocr_engine.extract_text(
                image_data=image_bytes
            )
            raw_text = ocr_result.text
        else:
            raise ValueError("Either image_base64 or text_content must be provided")
        
        # Step 2: Classify document
        if force_type:
            doc_type = force_type
            classification = DocumentClassification(
                document_type=force_type,
                confidence=1.0,
                reasoning="Manually specified",
                suggested_template=self.TEMPLATE_MAP.get(force_type, "unknown")
            )
        else:
            classification = await self._classify_document(raw_text)
            doc_type = classification.document_type
        
        if doc_type == SustainabilityDocumentType.UNKNOWN:
            return ExtractedData(
                document_type=doc_type,
                template="unknown",
                data={},
                raw_text=raw_text,
                confidence=classification.confidence,
                extraction_notes=["Could not determine document type"]
            )
        
        # Step 3: Extract structured data
        extracted = await self._extract_data(raw_text, doc_type)
        
        # Step 4: Calculate emissions
        co2e = self._calculate_emissions(extracted, doc_type)
        
        return ExtractedData(
            document_type=doc_type,
            template=self.TEMPLATE_MAP.get(doc_type, "unknown"),
            data=extracted,
            raw_text=raw_text,
            confidence=classification.confidence,
            calculated_co2e_kg=co2e
        )
    
    async def _classify_document(self, text: str) -> DocumentClassification:
        """Classify document using LLM."""
        if not self.llm_router:
            # Fallback to rule-based classification
            return self._rule_based_classification(text)
        
        prompt = CLASSIFICATION_PROMPT.format(text=text[:3000])  # Limit text length
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a document classification expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            if response.get("status") == "success":
                content = response["content"]
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    doc_type = SustainabilityDocumentType(result.get("document_type", "unknown"))
                    return DocumentClassification(
                        document_type=doc_type,
                        confidence=result.get("confidence", 0.5),
                        reasoning=result.get("reasoning", ""),
                        suggested_template=self.TEMPLATE_MAP.get(doc_type, "unknown"),
                        extracted_hints={"key_indicators": result.get("key_indicators", [])}
                    )
        except Exception as e:
            pass
        
        # Fallback
        return self._rule_based_classification(text)
    
    def _rule_based_classification(self, text: str) -> DocumentClassification:
        """Fallback rule-based classification."""
        text_lower = text.lower()
        
        # Keywords for each type
        patterns = {
            SustainabilityDocumentType.UTILITY_BILL_ELECTRIC: [
                "kwh", "kilowatt", "electric", "electricity", "power usage"
            ],
            SustainabilityDocumentType.UTILITY_BILL_GAS: [
                "therms", "ccf", "natural gas", "gas usage", "mcf"
            ],
            SustainabilityDocumentType.UTILITY_BILL_WATER: [
                "water usage", "gallons", "water bill", "sewer"
            ],
            SustainabilityDocumentType.FLIGHT_RECEIPT: [
                "flight", "airline", "boarding", "passenger", "departure", "arrival",
                "economy", "business class", "seat"
            ],
            SustainabilityDocumentType.CAR_RENTAL_RECEIPT: [
                "car rental", "vehicle rental", "rental agreement", "pickup", "return"
            ],
            SustainabilityDocumentType.FUEL_RECEIPT: [
                "gas station", "fuel", "petrol", "diesel", "gallons", "pump"
            ],
            SustainabilityDocumentType.SHIPPING_INVOICE: [
                "shipping", "freight", "tracking", "weight", "carrier", "shipment"
            ],
            SustainabilityDocumentType.EXPENSE_REPORT: [
                "expense report", "reimbursement", "expenses", "total expenses"
            ],
        }
        
        scores = {}
        for doc_type, keywords in patterns.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[doc_type] = score
        
        if scores:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] / 3, 1.0)  # Normalize
            return DocumentClassification(
                document_type=best_type,
                confidence=confidence,
                reasoning=f"Matched {scores[best_type]} keywords",
                suggested_template=self.TEMPLATE_MAP.get(best_type, "unknown")
            )
        
        return DocumentClassification(
            document_type=SustainabilityDocumentType.UNKNOWN,
            confidence=0.0,
            reasoning="No matching patterns found",
            suggested_template="unknown"
        )
    
    async def _extract_data(
        self, 
        text: str, 
        doc_type: SustainabilityDocumentType
    ) -> Dict[str, Any]:
        """Extract structured data using LLM."""
        if not self.llm_router or doc_type not in EXTRACTION_PROMPTS:
            return {"raw_text": text}
        
        prompt = EXTRACTION_PROMPTS[doc_type].format(text=text[:4000])
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Extract data precisely and respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            if response.get("status") == "success":
                content = response["content"]
                # Extract JSON
                json_match = re.search(r'[\[\{][\s\S]*[\]\}]', content)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            pass
        
        return {"raw_text": text, "extraction_error": "Failed to extract structured data"}
    
    def _calculate_emissions(
        self, 
        data: Dict[str, Any], 
        doc_type: SustainabilityDocumentType
    ) -> Optional[float]:
        """Calculate CO2e emissions from extracted data."""
        try:
            if doc_type == SustainabilityDocumentType.UTILITY_BILL_ELECTRIC:
                kwh = data.get("electricity_kwh", 0) or 0
                renewable = data.get("renewable_percent", 0) or 0
                return kwh * (1 - renewable/100) * self.EMISSION_FACTORS["electricity_us_avg"]
            
            elif doc_type == SustainabilityDocumentType.UTILITY_BILL_GAS:
                therms = data.get("natural_gas_therms", 0) or 0
                ccf = data.get("natural_gas_ccf", 0) or 0
                total = therms + ccf
                return total * self.EMISSION_FACTORS["natural_gas_therm"]
            
            elif doc_type == SustainabilityDocumentType.FLIGHT_RECEIPT:
                # Handle nested "flights" key or direct array/object
                if isinstance(data, dict) and "flights" in data:
                    flights = data["flights"]
                elif isinstance(data, list):
                    flights = data
                else:
                    flights = [data]
                
                total_co2e = 0
                
                for flight in flights:
                    # Estimate distance if not provided
                    distance = flight.get("distance_km")
                    if not distance:
                        # Try to look up from airport codes
                        origin = (flight.get("origin") or "").upper()[:3]
                        dest = (flight.get("destination") or "").upper()[:3]
                        distance = self.AIRPORT_DISTANCES.get((origin, dest), 2500)
                    
                    travel_class = (flight.get("travel_class") or "economy").lower()
                    factor_key = f"flight_{travel_class}_km"
                    factor = self.EMISSION_FACTORS.get(factor_key, self.EMISSION_FACTORS["flight_economy_km"])
                    
                    co2e = distance * factor
                    if flight.get("round_trip"):
                        co2e *= 2
                    
                    total_co2e += co2e
                
                return total_co2e
            
            elif doc_type == SustainabilityDocumentType.FUEL_RECEIPT:
                liters = data.get("fuel_liters", 0) or 0
                gallons = data.get("fuel_gallons", 0) or 0
                total_liters = liters + (gallons * 3.785)  # Convert gallons
                
                fuel_type = (data.get("fuel_type") or "petrol").lower()
                factor_key = f"fuel_{fuel_type}_liter"
                factor = self.EMISSION_FACTORS.get(factor_key, self.EMISSION_FACTORS["fuel_petrol_liter"])
                
                return total_liters * factor
            
            elif doc_type == SustainabilityDocumentType.SHIPPING_INVOICE:
                # Handle nested "shipments" key or direct array/object
                if isinstance(data, dict) and "shipments" in data:
                    shipments = data["shipments"]
                elif isinstance(data, list):
                    shipments = data
                else:
                    shipments = [data]
                
                total_co2e = 0
                
                for shipment in shipments:
                    weight_kg = shipment.get("weight_kg", 0) or 0
                    weight_lbs = shipment.get("weight_lbs", 0) or 0
                    weight = weight_kg + (weight_lbs * 0.4536)  # Convert lbs
                    
                    # Estimate distance if not provided
                    distance = shipment.get("distance_km")
                    if not distance:
                        # Try to estimate from origin/destination
                        distance = 5000  # Default assumption for international
                    
                    mode = (shipment.get("shipping_mode") or "road").lower()
                    
                    factor_key = f"shipping_{mode}_tkm"
                    factor = self.EMISSION_FACTORS.get(factor_key, self.EMISSION_FACTORS["shipping_road_tkm"])
                    
                    total_co2e += (weight / 1000) * distance * factor
                
                return total_co2e
            
            elif doc_type == SustainabilityDocumentType.ESG_REPORT:
                total_co2e = 0
                
                # Calculate from various metrics if available
                energy_kwh = data.get("total_energy_kwh", 0) or 0
                renewable_pct = data.get("renewable_energy_percent", 0) or 0
                total_co2e += energy_kwh * (1 - renewable_pct/100) * self.EMISSION_FACTORS["electricity_us_avg"]
                
                gas_therms = data.get("natural_gas_therms", 0) or 0
                total_co2e += gas_therms * self.EMISSION_FACTORS["natural_gas_therm"]
                
                travel_km = data.get("business_travel_km", 0) or 0
                total_co2e += travel_km * self.EMISSION_FACTORS["flight_economy_km"]
                
                fuel_gallons = data.get("fleet_fuel_gallons", 0) or 0
                fuel_liters = data.get("fleet_fuel_liters", 0) or 0
                total_fuel_liters = fuel_liters + (fuel_gallons * 3.785)
                total_co2e += total_fuel_liters * self.EMISSION_FACTORS["fuel_diesel_liter"]
                
                # Use pre-calculated emissions if provided
                if data.get("emissions_scope_1_kg"):
                    total_co2e = data.get("emissions_scope_1_kg", 0) + \
                                 data.get("emissions_scope_2_kg", 0) + \
                                 data.get("emissions_scope_3_kg", 0)
                
                return total_co2e if total_co2e > 0 else None
        
        except Exception:
            pass
        
        return None
    
    def get_supported_document_types(self) -> List[Dict[str, str]]:
        """Get list of supported document types."""
        return [
            {
                "type": dt.value,
                "name": dt.value.replace("_", " ").title(),
                "template": self.TEMPLATE_MAP.get(dt, "unknown")
            }
            for dt in SustainabilityDocumentType
            if dt != SustainabilityDocumentType.UNKNOWN
        ]


# Singleton instance
smart_processor = SmartDocumentProcessor()

