# -*- coding: utf-8 -*-
import csv
import os
import datetime
import requests
import pandas as pd


class UnsupportedYearException(Exception):
    pass


class UnsupportedZoneException(Exception):
    pass


class UnsupportedHolidayException(Exception):
    pass


class SchoolHolidayDates(object):
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
        super(SchoolHolidayDates, self).__init__()
        self.data = {}
        self.load_data(download, file)
        self.min_year = min(self.data.keys()).year
        self.max_year = max(self.data.keys()).year

    def load_data(self, download=False, file=None):
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
        if zone not in self.SUPPORTED_ZONES:
            raise UnsupportedZoneException("Unsupported zone: " + zone)
        return "vacances_zone_" + zone.lower()

    def check_name(self, name):
        if name not in self.SUPPORTED_HOLIDAY_NAMES:
            raise UnsupportedHolidayException("Unknown holiday name: " + name)

    def check_date(self, date):
        if isinstance(date, list) or isinstance(date, pd.Series):
            for d in date:
                self.check_date(d)
        else:
            if not isinstance(date, datetime.date):
                raise ValueError("date should be a datetime.date, a list of datetime.date, or a pandas Series of datetime.date")
            if date.year < self.min_year or date.year > self.max_year:
                raise UnsupportedYearException("No data for year: " + str(date.year))

    def is_holiday(self, date):
        self.check_date(date)
        if isinstance(date, list) or isinstance(date, pd.Series):
            return [d in self.data for d in date]
        else:
            return date in self.data

    def is_holiday(self, date):
        self.check_date(date)
        return date in self.data

    def is_holiday_for_zone(self, date, zone):
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
        if year < self.min_year or year > self.max_year:
            raise UnsupportedYearException("No data for year: " + str(year))
        return {k: v for k, v in self.data.items() if k.year == year}

    def holiday_for_year_by_name(self, year, name):
        self.check_name(name)

        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if v["nom_vacances"] == name
        }

    def holidays_for_year_and_zone(self, year, zone):
        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if self.is_holiday_for_zone(k, zone)
        }

    def holidays_for_year_zone_and_name(self, year, zone, name):
        self.check_name(name)

        return {
            k: v
            for k, v in self.holidays_for_year(year).items()
            if self.is_holiday_for_zone(k, zone) and v["nom_vacances"] == name
        }

    def holidays_between(self, start_date, end_date):
        """
        To get holidays between 2 dates
        :param start_date: the 1st bound of the interval
        :param end_date: the 2nd bound of the interval
        :return: dict
        """
        self.check_date(start_date)
        self.check_date(end_date)
        return {k: v for k, v in self.data.items() if start_date <= k <= end_date}
