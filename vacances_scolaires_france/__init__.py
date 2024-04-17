# -*- coding: utf-8 -*-
import csv
import os
import datetime
import requests
import pandas as pd

class UnsupportedYearException(Exception):
    """Exception raised when the year is not supported."""
    pass

class UnsupportedZoneException(Exception):
    """Exception raised when the zone is not supported."""
    pass

class UnsupportedHolidayException(Exception):
    """Exception raised when the holiday name is not supported."""
    pass

class SchoolHolidayDates(object):
    """A class to manage French school holiday dates."""
    SUPPORTED_ZONES = ["A", "B", "C"]
    SUPPORTED_HOLIDAY_NAMES = [
        "Vacances de Noël",
        "Vacances d'hiver",
        "Vacances de printemps",
        "Vacances d'été",
        "Vacances de la Toussaint",
        "Pont de l'Ascension",
    ]
    STABLE_URL = "https://www.data.gouv.fr/fr/datasets/r/c3781037-dffb-4789-9af9-15a955336771"
    BASE_FILE = os.path.join(os.path.dirname(__file__), "data/data.csv")

    def __init__(self, download=False, file=None):
        """Initializes the SchoolHolidayDates object.

        Args:
            download (bool): If True, download the data.
            file (str): Path to a custom file with holiday data.
        """
        super(SchoolHolidayDates, self).__init__()
        self.data = {}
        self.load_data(download, file)
        self.min_year = min(self.data.keys()).year
        self.max_year = max(self.data.keys()).year

    def load_data(self, download=False, file=None):
        """Loads holiday data from a file or URL.

        Args:
            download (bool): If True, download the data.
            file (str): Path to a custom file with holiday data.
        """
        if download:
            r = requests.get(SchoolHolidayDates.STABLE_URL, allow_redirects=True)
            open(file, 'wb').write(r.content)
        filename = file if file and os.path.isfile(file) else SchoolHolidayDates.BASE_FILE

        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = datetime.datetime.strptime(row["date"], "%Y-%m-%d").date()
                row["date"] = date

                # Only append rows where at least 1 zone is on holiday
                is_holiday = False
                for zone in self.SUPPORTED_ZONES:
                    zone_key = self.zone_key(zone)
                    row[zone_key] = row[zone_key] == "True"
                    is_holiday = is_holiday or row[zone_key]

                if is_holiday:
                    if len(row["nom_vacances"]) == 0:
                        raise ValueError("Holiday name not set for date: " + str(date))
                    self.data[date] = row

    def zone_key(self, zone):
        """Generates a key for the zone.

        Args:
            zone (str): The zone to generate the key for.

        Returns:
            str: The generated key for the zone.
        """
        if zone not in self.SUPPORTED_ZONES:
            raise UnsupportedZoneException("Unsupported zone: " + zone)
        return "vacances_zone_" + zone.lower()

    def check_name(self, name):
        """Checks if the holiday name is supported.

        Args:
            name (str): The name of the holiday.

        Raises:
            UnsupportedHolidayException: If the holiday name is not supported.
        """
        if name not in self.SUPPORTED_HOLIDAY_NAMES:
            raise UnsupportedHolidayException("Unknown holiday name: " + name)

    def check_date(self, date):
        """Checks if the date is within the supported range.

        Args:
            date (datetime.date | list | pd.Series): The date or dates to check.

        Raises:
            ValueError: If the date type is incorrect.
            UnsupportedYearException: If the year is not supported.
        """
        if isinstance(date, list) or isinstance(date, pd.Series):
            for d in date:
                self.check_date(d)
        else:
            if not isinstance(date, datetime.date):
                raise ValueError("date should be a datetime.date, a list of datetime.date, or a pandas Series of datetime.date")
            if date.year < self.min_year or date.year > self.max_year:
                raise UnsupportedYearException("No data for year: " + str(date.year))

    def is_holiday(self, date):
        """Checks if a date is a holiday.

        Args:
            date (datetime.date | list | pd.Series): The date or dates to check.

        Returns:
            bool | list: Whether the date(s) are holidays.
        """
        self.check_date(date)
        if isinstance(date, list) or isinstance(date, pd.Series):
            return [d in self.data for d in date]
        else:
            return date in self.data

    def is_holiday_for_zone(self, date, zone):
        """Checks if a date is a holiday for a specific zone.

        Args:
            date (datetime.date | list | pd.Series): The date or dates to check.
            zone (str): The zone to check for.

        Returns:
            bool | list: Whether the date(s) are holidays for the specified zone.
        """
        self.check_date(date)
        if isinstance(date, list) or isinstance(date, pd.Series):
            results = []
            for d in date:
                if d not in self.data:
                    results.append(False)
                else:
                    results.append(self.data[d][self.zone_key(zone)])
            return results
        else:
            if date not in self.data:
                return False
            return self.data[date][self.zone_key(zone)]

    def holidays_for_year(self, year):
        """Gets all holidays for a specific year.

        Args:
            year (int): The year to get holidays for.

        Returns:
            dict: A dictionary of holidays for the year.
        """
        if year < self.min_year or year > self.max_year:
            raise UnsupportedYearException("No data for year: " + str(year))
        return {k: v for k, v in self.data.items() if k.year == year}

    def holiday_for_year_by_name(self, year, name):
        """Gets holidays for a specific year by name.

        Args:
            year (int): The year to get holidays for.
            name (str): The name of the holiday.

        Returns:
            dict: A dictionary of holidays for the year with the specified name.
        """
        self.check_name(name)

        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if v["nom_vacances"] == name
        }

    def holidays_for_year_and_zone(self, year, zone):
        """Gets holidays for a specific year and zone.

        Args:
            year (int): The year to get holidays for.
            zone (str): The zone to get holidays for.

        Returns:
            dict: A dictionary of holidays for the year and zone.
        """
        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if self.is_holiday_for_zone(k, zone)
        }

    def holidays_for_year_zone_and_name(self, year, zone, name):
        """Gets holidays for a specific year, zone, and name.

        Args:
            year (int): The year to get holidays for.
            zone (str): The zone to get holidays for.
            name (str): The name of the holiday.

        Returns:
            dict: A dictionary of holidays for the year, zone, and name.
        """
        self.check_name(name)

        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if self.is_holiday_for_zone(k, zone) and v["nom_vacances"] == name
        }

    def holidays_between(self, start_date, end_date):
        """Gets holidays between two dates.

        Args:
            start_date (datetime.date): The start date of the interval.
            end_date (datetime.date): The end date of the interval.

        Returns:
            dict: A dictionary of holidays between the two dates.
        """
        self.check_date(start_date)
        self.check_date(end_date)
        return {k: v for k, v in self.data.items() if start_date <= k <= end_date}
