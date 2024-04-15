# -*- coding: utf-8 -*-
import csv
import os
import datetime
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

    def __init__(self):
        super(SchoolHolidayDates, self).__init__()
        self.data = {}
        self.load_data()
        self.min_year = min(self.data.keys()).year
        self.max_year = max(self.data.keys()).year

    def load_data(self):
        filename = os.path.join(os.path.dirname(__file__), "data/data.csv")

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
        
        res = {k: v for k, v in self.data.items() if k.year == year}

        return res

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
