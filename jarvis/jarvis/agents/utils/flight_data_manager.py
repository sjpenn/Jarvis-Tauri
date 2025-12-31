
import csv
import io
import httpx
from typing import Dict, Optional, Tuple

class FlightDataManager:
    """
    Manages static flight data from OpenFlights.org.
    
    Data Source: https://github.com/jpatokal/openflights/tree/master/data
    """
    
    AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
    AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
    
    def __init__(self):
        self._airlines: Dict[str, str] = {}  # ICAO/IATA -> Name
        self._airports: Dict[str, Dict[str, str]] = {}  # IATA -> {city, name, country}
        self._loaded = False
        
    async def load_data(self):
        """Download and parse OpenFlights data"""
        if self._loaded:
            return

        try:
            async with httpx.AsyncClient() as client:
                # Load Airlines
                # ID, Name, Alias, IATA, ICAO, CallSign, Country, Active
                resp = await client.get(self.AIRLINES_URL)
                if resp.status_code == 200:
                    reader = csv.reader(io.StringIO(resp.text))
                    for row in reader:
                        if len(row) >= 5:
                            name = row[1]
                            iata = row[3]
                            icao = row[4]
                            
                            if icao and icao != "\\N":
                                self._airlines[icao] = name
                            if iata and iata != "\\N":
                                self._airlines[iata] = name
                                
                # Load Airports
                # ID, Name, City, Country, IATA, ICAO, Lat, Lon, ...
                resp = await client.get(self.AIRPORTS_URL)
                if resp.status_code == 200:
                    reader = csv.reader(io.StringIO(resp.text))
                    for row in reader:
                        if len(row) >= 5:
                            name = row[1]
                            city = row[2]
                            country = row[3]
                            iata = row[4]
                            
                            if iata and iata != "\\N":
                                self._airports[iata] = {
                                    "name": name,
                                    "city": city,
                                    "country": country
                                }
                                
            self._loaded = True
            print(f"Loaded {len(self._airlines)} airlines and {len(self._airports)} airports from OpenFlights")
            
        except Exception as e:
            print(f"Failed to load OpenFlights data: {e}")

    def get_airline_name(self, code: str) -> Optional[str]:
        """Get airline name by IATA or ICAO code"""
        if not code:
            return None
        return self._airlines.get(code.upper())
    
    def get_airport_info(self, iata: str) -> Optional[Dict[str, str]]:
        """Get airport info by IATA code"""
        if not iata:
            return None
        return self._airports.get(iata.upper())
